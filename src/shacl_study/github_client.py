"""GitHub REST client for search and repository lookup.

Search responses are cached. Rate-limit headers are honored. The code-search
endpoint is the legacy API: 10 requests/minute and authentication required.
Other search endpoints allow 30 requests/minute when authenticated.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from shacl_study.models import SearchPage

API_ROOT = "https://api.github.com"
API_VERSION = "2026-03-10"
SEARCH_PATHS = {
    "code": "/search/code",
    "repository": "/search/repositories",
}
RESULT_CEILING = 1000
MAX_PER_PAGE = 100


class GitHubAuthError(RuntimeError):
    pass


class GitHubRequestError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class ArchiveTooLarge(RuntimeError):
    def __init__(self, size: int):
        super().__init__(f"Archive exceeds the configured size limit ({size} bytes).")
        self.size = size


class GitHubClient:
    def __init__(self, token: str, cache_dir: Path, *, timeout: float = 30.0):
        if not token.strip():
            raise GitHubAuthError("GITHUB_TOKEN is empty.")
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": API_VERSION,
                "User-Agent": "shacl-github-study",
            }
        )
        self._next_allowed: dict[str, float] = {}
        self.network_requests: dict[str, int] = {
            "core": 0,
            "code": 0,
            "repository": 0,
            "raw": 0,
            "codeload": 0,
        }
        self.network_bytes: dict[str, int] = {"raw": 0, "codeload": 0}

    def search(self, endpoint: str, query: str, *, page: int, per_page: int) -> SearchPage:
        if endpoint not in SEARCH_PATHS:
            raise ValueError(f"Unknown search endpoint: {endpoint}")
        url = API_ROOT + SEARCH_PATHS[endpoint]
        params = {"q": query, "page": page, "per_page": per_page}
        payload = self._request("GET", url, params, slot=endpoint)
        return SearchPage(
            total_count=int(payload.get("total_count") or 0),
            incomplete_results=bool(payload.get("incomplete_results")),
            items=list(payload.get("items") or []),
        )

    def get_repository(self, full_name: str) -> dict:
        safe = quote(full_name, safe="/")
        url = f"{API_ROOT}/repos/{safe}"
        return self._request("GET", url, None, slot="core")

    def resolve_commit(self, full_name: str, branch: str) -> dict:
        """Return the immutable commit SHA and its tree SHA for a branch head."""
        safe = quote(full_name, safe="/")
        ref = quote(branch, safe="")
        url = f"{API_ROOT}/repos/{safe}/commits/{ref}"
        payload = self._request("GET", url, None, slot="core")
        commit_sha = str(payload.get("sha") or "")
        tree_sha = str(((payload.get("commit") or {}).get("tree") or {}).get("sha") or "")
        if not commit_sha or not tree_sha:
            raise GitHubRequestError(200, "Commit response did not include an immutable sha.")
        return {"commit_sha": commit_sha, "tree_sha": tree_sha}

    def get_git_tree(self, full_name: str, tree_sha: str) -> dict:
        safe = quote(full_name, safe="/")
        url = f"{API_ROOT}/repos/{safe}/git/trees/{quote(tree_sha, safe='')}"
        return self._request("GET", url, {"recursive": "1"}, slot="core")

    def get_raw_file(self, full_name: str, commit_sha: str, path: str) -> bytes:
        return self._request_bytes(raw_content_url(full_name, commit_sha, path), slot="raw")

    def peek_raw_file(self, full_name: str, commit_sha: str, path: str, *, max_bytes: int = 65536) -> tuple[bytes, bool]:
        """Return a prefix and whether it is the complete file.

        Generic XML and JSON are sniffed from this prefix. A miss does not download the rest.
        """
        url = raw_content_url(full_name, commit_sha, path)
        cached = self._read_byte_cache(url)
        if cached is not None:
            if len(cached) <= max_bytes:
                return cached, True
            return cached[:max_bytes], False
        return self._request_prefix(url, max_bytes=max_bytes, slot="raw")

    def download_tarball(self, full_name: str, commit_sha: str, *, max_bytes: int) -> Path:
        url = tarball_url(full_name, commit_sha)
        cache = self._byte_cache_path(url)
        if cache.exists():
            size = cache.stat().st_size
            if size > max_bytes:
                raise ArchiveTooLarge(size)
            return cache
        cache.parent.mkdir(parents=True, exist_ok=True)
        partial = cache.with_suffix(".partial")
        last_error: Exception | None = None
        for attempt in range(4):
            self._wait_slot("codeload")
            try:
                response = self.session.get(
                    url,
                    headers=_binary_headers(self.session),
                    timeout=self.timeout,
                    stream=True,
                )
            except requests.RequestException as exc:
                last_error = exc
                time.sleep(min(2 ** attempt, 30))
                continue
            self.network_requests["codeload"] = self.network_requests.get("codeload", 0) + 1
            self._record_slot("codeload", response)
            if response.status_code == 200:
                total = 0
                try:
                    with partial.open("wb") as handle:
                        for chunk in response.iter_content(1024 * 1024):
                            if not chunk:
                                continue
                            total += len(chunk)
                            if total > max_bytes:
                                raise ArchiveTooLarge(total)
                            handle.write(chunk)
                except ArchiveTooLarge:
                    partial.unlink(missing_ok=True)
                    response.close()
                    raise
                partial.replace(cache)
                response.close()
                self.network_bytes["codeload"] = self.network_bytes.get("codeload", 0) + total
                return cache
            response.close()
            if response.status_code == 401:
                raise GitHubAuthError(_error_message(response))
            if response.status_code in {403, 429} and _is_rate_limit(response):
                time.sleep(_retry_delay(response, attempt))
                last_error = GitHubRequestError(response.status_code, _error_message(response))
                continue
            if response.status_code in {502, 503, 504}:
                time.sleep(min(2 ** attempt, 30))
                last_error = GitHubRequestError(response.status_code, _error_message(response))
                continue
            raise GitHubRequestError(response.status_code, _error_message(response))
        if isinstance(last_error, GitHubRequestError):
            raise last_error
        raise GitHubRequestError(0, f"Request failed: {last_error}")

    def _request(
        self,
        method: str,
        url: str,
        params: dict | None,
        *,
        slot: str,
    ) -> dict:
        cached = self._read_cache(method, url, params)
        if cached is not None:
            return cached

        last_error: Exception | None = None
        for attempt in range(4):
            self._wait_slot(slot)
            try:
                response = self.session.request(method, url, params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                last_error = exc
                time.sleep(min(2 ** attempt, 30))
                continue

            self._record_slot(slot, response)
            self.network_requests[slot] = self.network_requests.get(slot, 0) + 1
            if response.status_code == 200:
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise GitHubRequestError(response.status_code, "Response was not JSON.") from exc
                self._write_cache(method, url, params, payload)
                return payload

            if response.status_code == 401:
                raise GitHubAuthError(_error_message(response))

            if response.status_code in {403, 429} and _is_rate_limit(response):
                delay = _retry_delay(response, attempt)
                time.sleep(delay)
                last_error = GitHubRequestError(response.status_code, _error_message(response))
                continue

            if response.status_code in {502, 503, 504}:
                time.sleep(min(2 ** attempt, 30))
                last_error = GitHubRequestError(response.status_code, _error_message(response))
                continue

            raise GitHubRequestError(response.status_code, _error_message(response))

        if isinstance(last_error, GitHubRequestError):
            raise last_error
        raise GitHubRequestError(0, f"Request failed: {last_error}")

    def _wait_slot(self, slot: str) -> None:
        ready_at = self._next_allowed.get(slot, 0.0)
        delay = ready_at - time.monotonic()
        if delay > 0:
            time.sleep(delay)

    def _record_slot(self, slot: str, response: requests.Response) -> None:
        remaining = _header_int(response, "X-RateLimit-Remaining")
        reset = _header_int(response, "X-RateLimit-Reset")
        if remaining == 0 and reset is not None:
            self._next_allowed[slot] = time.monotonic() + max(0.0, reset - time.time()) + 1.0
            return
        # Stay under the documented search ceilings between uncached calls.
        minimum = {"code": 6.2, "repository": 2.1, "core": 0.0, "raw": 0.05, "codeload": 0.2}.get(slot, 0.0)
        self._next_allowed[slot] = time.monotonic() + minimum

    def _cache_key(self, method: str, url: str, params: dict | None) -> str:
        raw = json.dumps(
            {"method": method, "url": url, "params": params or {}},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _cache_file(self, method: str, url: str, params: dict | None) -> Path:
        return self.cache_dir / f"{self._cache_key(method, url, params)}.json"

    def _read_cache(self, method: str, url: str, params: dict | None) -> dict | None:
        path = self._cache_file(method, url, params)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_cache(self, method: str, url: str, params: dict | None, payload: dict) -> None:
        path = self._cache_file(method, url, params)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def _request_bytes(self, url: str, *, slot: str) -> bytes:
        cached = self._read_byte_cache(url)
        if cached is not None:
            return cached
        last_error: Exception | None = None
        for attempt in range(4):
            self._wait_slot(slot)
            try:
                response = self.session.get(
                    url,
                    headers=_binary_headers(self.session),
                    timeout=self.timeout,
                )
            except requests.RequestException as exc:
                last_error = exc
                time.sleep(min(2 ** attempt, 30))
                continue
            self.network_requests[slot] = self.network_requests.get(slot, 0) + 1
            self._record_slot(slot, response)
            if response.status_code == 200:
                payload = response.content
                self.network_bytes[slot] = self.network_bytes.get(slot, 0) + len(payload)
                self._write_byte_cache(url, payload)
                return payload
            if response.status_code == 401:
                raise GitHubAuthError(_error_message(response))
            if response.status_code in {403, 429} and _is_rate_limit(response):
                time.sleep(_retry_delay(response, attempt))
                last_error = GitHubRequestError(response.status_code, _error_message(response))
                continue
            if response.status_code in {502, 503, 504}:
                time.sleep(min(2 ** attempt, 30))
                last_error = GitHubRequestError(response.status_code, _error_message(response))
                continue
            raise GitHubRequestError(response.status_code, _error_message(response))
        if isinstance(last_error, GitHubRequestError):
            raise last_error
        raise GitHubRequestError(0, f"Request failed: {last_error}")

    def _request_prefix(self, url: str, *, max_bytes: int, slot: str) -> tuple[bytes, bool]:
        last_error: Exception | None = None
        range_header = {"Range": f"bytes=0-{max_bytes - 1}"}
        for attempt in range(4):
            self._wait_slot(slot)
            try:
                response = self.session.get(
                    url,
                    headers={**_binary_headers(self.session), **range_header},
                    timeout=self.timeout,
                    stream=True,
                )
            except requests.RequestException as exc:
                last_error = exc
                time.sleep(min(2 ** attempt, 30))
                continue
            self.network_requests[slot] = self.network_requests.get(slot, 0) + 1
            self._record_slot(slot, response)
            try:
                if response.status_code in {200, 206}:
                    payload = _read_limited(response, max_bytes)
                    self.network_bytes[slot] = self.network_bytes.get(slot, 0) + len(payload)
                    complete = _prefix_is_complete(response, payload, max_bytes)
                    if complete:
                        self._write_byte_cache(url, payload)
                    return payload, complete
                if response.status_code == 401:
                    raise GitHubAuthError(_error_message(response))
                if response.status_code in {403, 429} and _is_rate_limit(response):
                    time.sleep(_retry_delay(response, attempt))
                    last_error = GitHubRequestError(response.status_code, _error_message(response))
                    continue
                if response.status_code in {502, 503, 504}:
                    time.sleep(min(2 ** attempt, 30))
                    last_error = GitHubRequestError(response.status_code, _error_message(response))
                    continue
                raise GitHubRequestError(response.status_code, _error_message(response))
            finally:
                response.close()
        if isinstance(last_error, GitHubRequestError):
            raise last_error
        raise GitHubRequestError(0, f"Request failed: {last_error}")

    def _byte_cache_path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / "bytes" / digest

    def _read_byte_cache(self, url: str) -> bytes | None:
        path = self._byte_cache_path(url)
        if not path.exists():
            return None
        return path.read_bytes()

    def _write_byte_cache(self, url: str, payload: bytes) -> None:
        path = self._byte_cache_path(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


def _header_int(response: requests.Response, name: str) -> int | None:
    value = response.headers.get(name)
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _error_message(response: requests.Response) -> str:
    try:
        payload: Any = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict) and payload.get("message"):
        return f"HTTP {response.status_code}: {payload['message']}"
    text = response.text.strip().replace("\n", " ")
    return f"HTTP {response.status_code}: {text[:300]}"


def _is_rate_limit(response: requests.Response) -> bool:
    message = _error_message(response).lower()
    if "rate limit" in message:
        return True
    remaining = response.headers.get("X-RateLimit-Remaining")
    return remaining == "0"


def _read_limited(response: requests.Response, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    remaining = max_bytes
    for chunk in response.iter_content(65536):
        if not chunk or remaining <= 0:
            break
        chunks.append(chunk[:remaining])
        remaining -= len(chunks[-1])
    return b"".join(chunks)


def _prefix_is_complete(response: requests.Response, payload: bytes, max_bytes: int) -> bool:
    if response.status_code == 206:
        total = _content_range_total(response.headers.get("Content-Range", ""))
        return total is not None and total <= len(payload)
    if len(payload) < max_bytes:
        return True
    declared = response.headers.get("Content-Length")
    return declared is not None and declared.isdigit() and int(declared) <= len(payload)


def _content_range_total(header: str) -> int | None:
    # bytes 0-65535/90000
    if "/" not in header:
        return None
    total = header.rsplit("/", 1)[-1].strip()
    if total.isdigit():
        return int(total)
    return None


def raw_content_url(full_name: str, commit_sha: str, path: str) -> str:
    """Fetch a blob by immutable commit SHA. A branch name is not a pin."""
    safe_repo = quote(full_name, safe="/")
    safe_path = "/".join(quote(part) for part in path.split("/"))
    return f"https://raw.githubusercontent.com/{safe_repo}/{commit_sha}/{safe_path}"


def tarball_url(full_name: str, commit_sha: str) -> str:
    safe_repo = quote(full_name, safe="/")
    return f"https://codeload.github.com/{safe_repo}/tar.gz/{commit_sha}"


def _binary_headers(session: requests.Session) -> dict[str, str]:
    headers = {
        "Accept": "application/octet-stream",
        "User-Agent": "shacl-github-study",
    }
    authorization = session.headers.get("Authorization")
    if authorization:
        headers["Authorization"] = authorization
    return headers


def _retry_delay(response: requests.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return float(retry_after) + 1.0
        except ValueError:
            pass
    reset = _header_int(response, "X-RateLimit-Reset")
    if reset is not None:
        return max(1.0, reset - time.time()) + 1.0
    return min(2 ** attempt, 60)
