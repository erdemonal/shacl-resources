"""Authenticated sanity check for seven discovery queries.

This does not verify SHACL and does not write the candidate corpus.
The token is read from the environment and is never printed.
"""

from __future__ import annotations

import base64
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from shacl_study.discovery import load_config, plan_queries
from shacl_study.github_client import API_VERSION

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.github.com"
PER_PAGE = 20
SAMPLE_SIZE = 15
RESULT_CEILING = 1000

CHECKS = [
    ("code__canonical_namespace__primary__ext_ttl", "namespace"),
    ("code__class_node_shape__primary__ext_ttl", "node_shape"),
    ("code__class_property_shape__primary__ext_ttl", "property_shape"),
    ("code__term_target_class__primary__ext_ttl", "target_class"),
    ("code__broad_shacl__primary", "broad_code"),
    ("repository__topic_shacl", "topic"),
    ("repository__broad_shacl", "broad_repo"),
]


def main() -> None:
    token = _token()
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/vnd.github.text-match+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "shacl-github-study",
        }
    )
    planned = {item.query_id: item for item in plan_queries(load_config(ROOT / "config" / "discovery_queries.yaml"))}
    rate_limits: list[dict] = []
    reports = []
    for query_id, kind in CHECKS:
        query = planned[query_id]
        page, rate = _search(session, query.endpoint, query.query_text)
        rate_limits.append(rate)
        reports.append(_assess(session, query, kind, page, rate_limits))
        _pause(query.endpoint)

    topic = next(item for item in reports if item["kind"] == "topic")
    fork_probe = None
    if topic["forks_in_fetched"] == 0 and topic["status"] == 200:
        page, rate = _search(session, "repository", "topic:shacl is:public fork:only")
        rate_limits.append(rate)
        items = page.get("items") or []
        fork_probe = {
            "query": "topic:shacl is:public fork:only",
            "endpoint": "repository",
            "status": page.get("_status"),
            "total_count": page.get("total_count"),
            "incomplete_results": page.get("incomplete_results"),
            "fetched": len(items),
            "forks_in_fetched": sum(1 for item in items if item.get("fork") is True),
            "sample_names": [item.get("full_name") for item in items[:5]],
        }

    payload = {
        "collected_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "per_page": PER_PAGE,
        "sample_size": SAMPLE_SIZE,
        "sample_rule": "first results in GitHub best-match order on page 1",
        "rate_limits": rate_limits,
        "fork_only_probe": fork_probe,
        "queries": reports,
    }
    out_dir = ROOT / "data" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "query_sanity_pilot.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    note = _markdown(payload)
    (ROOT / "notes" / "query-sanity-pilot.md").write_text(note, encoding="utf-8")
    print(note)


def _token() -> str:
    if not os.environ.get("GITHUB_TOKEN"):
        env_path = ROOT / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("GITHUB_TOKEN="):
                    os.environ["GITHUB_TOKEN"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise SystemExit("GITHUB_TOKEN is empty.")
    return token


def _search(session: requests.Session, endpoint: str, query: str) -> tuple[dict, dict]:
    path = "/search/code" if endpoint == "code" else "/search/repositories"
    response = _request(session, "GET", API + path, params={"q": query, "per_page": PER_PAGE, "page": 1})
    rate = _rate(response, endpoint)
    try:
        body = response.json()
    except ValueError:
        body = {"message": response.text[:300]}
    if not isinstance(body, dict):
        body = {"message": "Response was not a JSON object."}
    body["_status"] = response.status_code
    return body, rate


def _request(
    session: requests.Session,
    method: str,
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
) -> requests.Response:
    for attempt in range(4):
        response = session.request(method, url, params=params, headers=headers, timeout=45)
        if response.status_code in {403, 429} and _rate_limited(response):
            time.sleep(_retry_delay(response, attempt))
            continue
        if response.status_code in {502, 503, 504}:
            time.sleep(min(2 ** attempt, 20))
            continue
        return response
    return response


def _assess(session, query, kind: str, page: dict, rate_limits: list[dict]) -> dict:
    items = page.get("items") if isinstance(page.get("items"), list) else []
    total = page.get("total_count")
    status = page.get("_status")
    sample_items = items[:SAMPLE_SIZE]
    checked = []
    for item in sample_items:
        if query.endpoint == "code":
            checked.append(_check_code(session, item, kind, rate_limits))
        else:
            checked.append(_check_repo(session, item, kind, rate_limits))
    with_literal = sum(1 for row in checked if row["intended_literal"])
    without_literal = sum(1 for row in checked if row["content_checked"] and not row["intended_literal"])
    fetch_failures = sum(1 for row in checked if not row["content_checked"])
    return {
        "query_id": query.query_id,
        "kind": kind,
        "endpoint": query.endpoint,
        "query": query.query_text,
        "status": status,
        "reported_total": total,
        "incomplete_results": page.get("incomplete_results"),
        "error_message": page.get("message") if status != 200 else "",
        "ceiling_relevant": isinstance(total, int) and total >= RESULT_CEILING,
        "fetched": len(items),
        "forks_in_fetched": _fork_count(items, query.endpoint),
        "sample_checked": sum(1 for row in checked if row["content_checked"]),
        "sample_with_intended_literal": with_literal,
        "sample_without_intended_literal": without_literal,
        "sample_fetch_failures": fetch_failures,
        "samples": checked,
    }


def _check_code(session, item: dict, kind: str, rate_limits: list[dict]) -> dict:
    repo = item.get("repository") if isinstance(item.get("repository"), dict) else {}
    text, fetch_note, rate = _file_text(session, item)
    if rate:
        rate_limits.append(rate)
    intended, detail = (False, "file text unavailable") if text is None else _literal(text, kind)
    fragments = _fragments(item)
    return {
        "repository": repo.get("full_name"),
        "path": item.get("path"),
        "fork": repo.get("fork"),
        "content_checked": text is not None,
        "intended_literal": intended,
        "detail": detail,
        "match_fragment": fragments,
        "fetch_note": fetch_note,
    }


def _check_repo(session, item: dict, kind: str, rate_limits: list[dict]) -> dict:
    text_parts = [
        str(item.get("full_name") or ""),
        str(item.get("description") or ""),
        " ".join(item.get("topics") or []),
    ]
    readme = ""
    fetch_note = "search metadata only"
    if kind == "broad_repo":
        response = _request(
            session,
            "GET",
            f"{API}/repos/{item.get('full_name')}/readme",
            headers={"Accept": "application/vnd.github.raw"},
        )
        rate_limits.append(_rate(response, "core"))
        if response.status_code == 200:
            readme = response.text
            fetch_note = "readme fetched"
        else:
            fetch_note = f"readme HTTP {response.status_code}"
    combined = "\n".join(text_parts + [readme])
    if kind == "topic":
        topics = [str(topic).lower() for topic in item.get("topics") or []]
        if "shacl" in topics:
            intended, detail = True, "topic list contains shacl"
        elif item.get("topics") is None:
            intended, detail = False, "search result did not include topics"
        else:
            intended, detail = False, "topic list does not contain shacl"
        content_checked = item.get("topics") is not None
    else:
        intended, detail = _literal(combined, kind)
        content_checked = True
    return {
        "repository": item.get("full_name"),
        "path": "",
        "fork": item.get("fork"),
        "content_checked": content_checked,
        "intended_literal": intended,
        "detail": detail,
        "match_fragment": _snippet(combined, "shacl") if kind == "broad_repo" else "",
        "fetch_note": fetch_note,
    }


def _file_text(session, item: dict) -> tuple[str | None, str, dict | None]:
    git_url = item.get("git_url")
    if not git_url:
        return None, "no git_url", None
    response = _request(session, "GET", git_url, headers={"Accept": "application/vnd.github+json"})
    rate = _rate(response, "core")
    if response.status_code != 200:
        return None, f"blob HTTP {response.status_code}", rate
    try:
        body = response.json()
    except ValueError:
        return None, "blob was not JSON", rate
    if body.get("encoding") != "base64" or not isinstance(body.get("content"), str):
        return None, "blob had no base64 content", rate
    try:
        text = base64.b64decode(body["content"]).decode("utf-8", errors="replace")
    except ValueError:
        return None, "blob base64 decode failed", rate
    return text, "blob fetched", rate


def _literal(text: str, kind: str) -> tuple[bool, str]:
    namespace = "http://www.w3.org/ns/shacl#"
    if kind == "namespace":
        return (namespace in text, "full SHACL namespace IRI" if namespace in text else "namespace IRI absent")
    if kind == "node_shape":
        found = "sh:NodeShape" in text or f"{namespace}NodeShape" in text
        return found, _which(text, "sh:NodeShape", f"{namespace}NodeShape")
    if kind == "property_shape":
        found = "sh:PropertyShape" in text or f"{namespace}PropertyShape" in text
        return found, _which(text, "sh:PropertyShape", f"{namespace}PropertyShape")
    if kind == "target_class":
        found = "sh:targetClass" in text or f"{namespace}targetClass" in text
        return found, _which(text, "sh:targetClass", f"{namespace}targetClass")
    if kind in {"broad_code", "broad_repo"}:
        found = "shacl" in text.lower()
        return found, _snippet(text, "shacl") if found else "SHACL absent from inspected text"
    return False, "unknown check"


def _which(text: str, prefixed: str, full_iri: str) -> str:
    hits = []
    if prefixed in text:
        hits.append(prefixed)
    if full_iri in text:
        hits.append(full_iri)
    return ", ".join(hits) if hits else "intended literal absent"


def _snippet(text: str, needle: str) -> str:
    index = text.lower().find(needle.lower())
    if index < 0:
        return ""
    start = max(0, index - 50)
    end = min(len(text), index + len(needle) + 50)
    return " ".join(text[start:end].split())[:180]


def _fragments(item: dict) -> str:
    matches = item.get("text_matches") if isinstance(item.get("text_matches"), list) else []
    parts = []
    for match in matches[:2]:
        if isinstance(match, dict) and match.get("fragment"):
            parts.append(" ".join(str(match["fragment"]).split())[:180])
    return " | ".join(parts)


def _fork_count(items: list[dict], endpoint: str) -> int:
    count = 0
    for item in items:
        repo = item.get("repository") if endpoint == "code" else item
        if isinstance(repo, dict) and repo.get("fork") is True:
            count += 1
    return count


def _pause(endpoint: str) -> None:
    time.sleep(7.0 if endpoint == "code" else 2.5)


def _rate(response: requests.Response, endpoint: str) -> dict:
    return {
        "endpoint": endpoint,
        "status": response.status_code,
        "resource": response.headers.get("X-RateLimit-Resource"),
        "limit": response.headers.get("X-RateLimit-Limit"),
        "remaining": response.headers.get("X-RateLimit-Remaining"),
        "reset": response.headers.get("X-RateLimit-Reset"),
    }


def _rate_limited(response: requests.Response) -> bool:
    message = ""
    try:
        body = response.json()
        if isinstance(body, dict):
            message = str(body.get("message") or "")
    except ValueError:
        message = response.text
    return "rate limit" in message.lower() or response.headers.get("X-RateLimit-Remaining") == "0"


def _retry_delay(response: requests.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return float(retry_after) + 1
        except ValueError:
            pass
    reset = response.headers.get("X-RateLimit-Reset")
    if reset:
        try:
            return max(1.0, float(reset) - time.time()) + 1
        except ValueError:
            pass
    return min(2 ** attempt, 30)


def _markdown(payload: dict) -> str:
    lines = [
        "# Query sanity pilot",
        "",
        "Authenticated page-1 check of seven discovery queries. This does not verify SHACL and does not decide corpus inclusion.",
        "",
        f"Collected at {payload['collected_at']}. Each search requested page 1 with per_page={payload['per_page']}. File and metadata checks use the first {payload['sample_size']} results in GitHub best-match order.",
        "",
        "| query_id | query | reported_total | sample_checked | sample_with_intended_literal | sample_without_intended_literal | notes |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in payload["queries"]:
        notes = _notes(row)
        lines.append(
            "| {query_id} | `{query}` | {reported_total} | {sample_checked} | {sample_with_intended_literal} | {sample_without_intended_literal} | {notes} |".format(
                notes=notes.replace("|", "/"),
                **row,
            )
        )
    lines.extend(["", "## Rate limits", ""])
    seen = []
    for rate in payload["rate_limits"]:
        key = (rate.get("resource"), rate.get("limit"))
        if key in seen or not rate.get("resource"):
            continue
        seen.append(key)
        lines.append(
            f"- resource `{rate['resource']}`: limit {rate['limit']}, remaining {rate['remaining']} after a {rate['status']} response on `{rate['endpoint']}`"
        )
    lines.extend(["", "## Forks", ""])
    for row in payload["queries"]:
        lines.append(
            f"- `{row['query_id']}`: {row['forks_in_fetched']} of {row['fetched']} fetched results are forks."
        )
    probe = payload.get("fork_only_probe")
    if probe:
        lines.append(
            f"- Extra probe `{probe['query']}`: total_count={probe['total_count']}, fetched={probe['fetched']}, forks_in_fetched={probe['forks_in_fetched']}."
        )
    lines.extend(["", "## Samples", ""])
    for row in payload["queries"]:
        lines.append(f"### {row['query_id']}")
        lines.append("")
        lines.append(
            f"endpoint `{row['endpoint']}`; incomplete_results={row['incomplete_results']}; ceiling_relevant={row['ceiling_relevant']}; fetched={row['fetched']}."
        )
        if row["error_message"]:
            lines.append(f"API message: {row['error_message']}")
        lines.append("")
        for sample in row["samples"]:
            mark = "literal" if sample["intended_literal"] else "no-literal"
            if not sample["content_checked"]:
                mark = "not-checked"
            location = sample["repository"] or ""
            if sample["path"]:
                location = f"{location}:{sample['path']}"
            fork = " fork" if sample["fork"] else ""
            lines.append(f"- {mark}{fork} `{location}` — {sample['detail']}")
            if sample["match_fragment"]:
                lines.append(f"  - highlighted: {sample['match_fragment']}")
        lines.append("")
    lines.append("No discovery query was changed.")
    lines.append("")
    return "\n".join(lines)


def _notes(row: dict) -> str:
    parts = []
    if row["status"] != 200:
        parts.append(f"HTTP {row['status']}")
    if row["incomplete_results"]:
        parts.append("incomplete_results")
    if row["ceiling_relevant"]:
        parts.append("total_count is at or above 1000")
    else:
        parts.append("under the 1000 ceiling")
    if row["sample_fetch_failures"]:
        parts.append(f"{row['sample_fetch_failures']} files not fetched")
    parts.append(f"{row['forks_in_fetched']}/{row['fetched']} fetched are forks")
    return "; ".join(parts)


if __name__ == "__main__":
    main()
