"""Plan and run repository discovery. This module does not verify SHACL."""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from math import ceil
from pathlib import Path

import yaml

from shacl_study.github_client import RESULT_CEILING, GitHubAuthError, GitHubRequestError
from shacl_study.models import (
    Candidate,
    DiscoveryState,
    NonPublicHit,
    PlannedQuery,
    QueryExecution,
)
from shacl_study.storage import export_results, load_state, save_state, state_path

FINISHED = {"ok", "truncated", "split"}


def load_config(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Discovery config must be a mapping: {path}")
    return payload


def config_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plan_queries(config: dict) -> list[PlannedQuery]:
    planned: list[PlannedQuery] = []
    code = config["code_search"]
    extensions = list(code["extensions"])
    for spec in code["queries"]:
        if spec.get("partition_by_extension"):
            slices = extensions
        else:
            slices = [None]
        for stream in code["fork_streams"]:
            qualifier = str(stream.get("qualifier") or "").strip()
            stream_id = str(stream["id"])
            if qualifier == "fork:true":
                raise ValueError("Code search must not use fork:true. Use a primary stream and fork:only.")
            if stream_id not in {"primary", "fork_only"}:
                raise ValueError(f"Unknown code-search fork stream: {stream_id}")
            for extension in slices:
                planned.append(
                    _planned(
                        endpoint="code",
                        base_id=spec["id"],
                        family=spec["family"],
                        term=spec["term"],
                        extension=extension,
                        fork_qualifier=qualifier or None,
                        fork_stream=stream_id,
                        content_qualifier=code["content_qualifier"],
                        allow_date_partition=False,
                    )
                )

    repositories = config["repository_search"]
    for spec in repositories["queries"]:
        planned.append(
            _planned(
                endpoint="repository",
                base_id=spec["id"],
                family=spec["family"],
                term=spec["term"],
                extension=None,
                fork_qualifier=repositories["fork_qualifier"],
                fork_stream="",
                public_qualifier=repositories["public_qualifier"],
                allow_date_partition=bool(spec.get("date_partition")),
            )
        )
    return planned


def split_created_range(start: date, end: date) -> tuple[tuple[date, date], tuple[date, date]] | None:
    if end <= start:
        return None
    midpoint = start + timedelta(days=(end - start).days // 2)
    right_start = midpoint + timedelta(days=1)
    if right_start > end:
        return None
    return (start, midpoint), (right_start, end)


def select_queries(planned: list[PlannedQuery], query_ids: list[str] | None) -> list[PlannedQuery]:
    if not query_ids:
        return planned
    selected = []
    for item in planned:
        if any(item.query_id == query_id or item.query_id.startswith(f"{query_id}__") for query_id in query_ids):
            selected.append(item)
    return selected


def run_discovery(
    *,
    config: dict,
    config_sha256: str,
    client,
    data_dir: Path,
    fresh: bool,
    per_page: int,
    max_pages: int | None,
    query_ids: list[str] | None,
    window_end: date,
    clock: Callable[[], datetime] | None = None,
    logger: logging.Logger | None = None,
) -> DiscoveryState:
    if per_page < 1 or per_page > 100:
        raise ValueError("per_page must be between 1 and 100.")
    log = logger or logging.getLogger("shacl_study")
    now = clock or (lambda: datetime.now(timezone.utc))
    window_start = date.fromisoformat(config["repository_search"]["date_partition_start"])
    path = state_path(data_dir)
    state = None if fresh else load_state(path)
    if state is None:
        state = DiscoveryState(
            config_sha256=config_sha256,
            partition_window_start=window_start.isoformat(),
            partition_window_end=window_end.isoformat(),
        )
    elif state.config_sha256 != config_sha256:
        raise ValueError("Discovery config changed since the saved run. Pass --fresh to start over.")

    planned = select_queries(plan_queries(config), query_ids)
    if query_ids and not planned:
        raise ValueError("No planned query matches --query-id.")
    try:
        for query in planned:
            _execute_query(
                query,
                state=state,
                client=client,
                per_page=per_page,
                max_pages=max_pages,
                window_start=date.fromisoformat(state.partition_window_start),
                window_end=date.fromisoformat(state.partition_window_end),
                clock=now,
                log=log,
                data_dir=data_dir,
            )
    except GitHubAuthError:
        _persist(state, data_dir)
        raise

    _hydrate(state, client, log=log)
    _persist(state, data_dir)
    return state


def _execute_query(
    query: PlannedQuery,
    *,
    state: DiscoveryState,
    client,
    per_page: int,
    max_pages: int | None,
    window_start: date,
    window_end: date,
    clock: Callable[[], datetime],
    log: logging.Logger,
    data_dir: Path,
) -> None:
    existing = state.executions.get(query.query_id)
    if existing and existing.api_status == "split":
        for child in _date_children(query, window_start, window_end):
            _execute_query(
                child,
                state=state,
                client=client,
                per_page=per_page,
                max_pages=max_pages,
                window_start=window_start,
                window_end=window_end,
                clock=clock,
                log=log,
                data_dir=data_dir,
            )
        return
    if existing and existing.api_status in FINISHED:
        log.info("skip completed query %s", query.query_id)
        return

    log.info("search %s %s", query.endpoint, query.query_text)
    try:
        first = client.search(query.endpoint, query.query_text, page=1, per_page=per_page)
    except GitHubRequestError as exc:
        _record_execution(
            state,
            query,
            clock=clock,
            result_count=None,
            pages=0,
            incomplete=None,
            truncated=False,
            reason=exc.message,
            status="error",
        )
        _persist(state, data_dir)
        log.warning("query failed %s: %s", query.query_id, exc.message)
        return

    reasons: list[str] = []
    if first.incomplete_results:
        reasons.append("incomplete_results")
    ceiling = first.total_count >= RESULT_CEILING
    if ceiling:
        reasons.append("result_ceiling")

    pages_needed = _pages_needed(first.total_count, per_page)
    page_limit = pages_needed if max_pages is None else min(pages_needed, max_pages)
    local_limit = page_limit < pages_needed
    if local_limit:
        reasons.append("local_page_limit")

    if (
        query.allow_date_partition
        and query.endpoint == "repository"
        and ceiling
        and not local_limit
    ):
        children = _date_children(query, window_start, window_end)
        if children:
            _record_execution(
                state,
                query,
                clock=clock,
                result_count=first.total_count,
                pages=1,
                incomplete=first.incomplete_results,
                truncated=True,
                reason="|".join(reasons),
                status="split",
            )
            _persist(state, data_dir)
            log.info("split %s into %s date partitions", query.query_id, len(children))
            for child in children:
                _execute_query(
                    child,
                    state=state,
                    client=client,
                    per_page=per_page,
                    max_pages=max_pages,
                    window_start=window_start,
                    window_end=window_end,
                    clock=clock,
                    log=log,
                    data_dir=data_dir,
                )
            return
        reasons.append("unsplittable_date_window")

    pages = [first]
    for page_number in range(2, page_limit + 1):
        try:
            pages.append(
                client.search(query.endpoint, query.query_text, page=page_number, per_page=per_page)
            )
        except GitHubRequestError as exc:
            reasons.append("page_error")
            log.warning("page %s failed for %s: %s", page_number, query.query_id, exc.message)
            break
        if pages[-1].incomplete_results and "incomplete_results" not in reasons:
            reasons.append("incomplete_results")

    seen_at = _stamp(clock)
    for page in pages:
        for item in page.items:
            _observe_item(state, query, item, seen_at)

    truncated = bool(reasons)
    status = "truncated" if truncated else "ok"
    _record_execution(
        state,
        query,
        clock=clock,
        result_count=first.total_count,
        pages=len(pages),
        incomplete=any(page.incomplete_results for page in pages),
        truncated=truncated,
        reason="|".join(dict.fromkeys(reasons)),
        status=status,
    )
    _persist(state, data_dir)


def _observe_item(state: DiscoveryState, query: PlannedQuery, item: dict, seen_at: str) -> None:
    repo = item.get("repository") if query.endpoint == "code" else item
    if not isinstance(repo, dict) or repo.get("id") is None or not repo.get("full_name"):
        return
    if not _looks_public(repo):
        _merge_nonpublic(state, repo, [query.query_id], "not_public")
        return
    _merge_candidate(state, repo, query, seen_at)


def _merge_candidate(state: DiscoveryState, repo: dict, query: PlannedQuery, seen_at: str) -> None:
    key = str(repo["id"])
    provenance = _provenance(query)
    current = state.candidates.get(key)
    if current is None:
        state.candidates[key] = Candidate(
            repository_id=int(repo["id"]),
            repository_full_name=str(repo["full_name"]),
            repository_url=str(repo.get("html_url") or f"https://github.com/{repo['full_name']}"),
            default_branch=str(repo.get("default_branch") or ""),
            discovered_by=[provenance],
            discovery_queries=[query.query_id],
            first_seen_at=seen_at,
            last_seen_at=seen_at,
            is_fork=repo.get("fork") if isinstance(repo.get("fork"), bool) else None,
            archived=repo.get("archived") if isinstance(repo.get("archived"), bool) else None,
            stars=repo.get("stargazers_count") if isinstance(repo.get("stargazers_count"), int) else None,
            license=_license_name(repo),
            created_at=str(repo.get("created_at") or ""),
            updated_at=str(repo.get("updated_at") or ""),
            pushed_at=str(repo.get("pushed_at") or ""),
        )
        return
    if provenance not in current.discovered_by:
        current.discovered_by.append(provenance)
    if query.query_id not in current.discovery_queries:
        current.discovery_queries.append(query.query_id)
    if seen_at > current.last_seen_at:
        current.last_seen_at = seen_at


def _merge_nonpublic(state: DiscoveryState, repo: dict, query_ids: list[str], reason: str) -> None:
    key = str(repo["id"])
    current = state.nonpublic.get(key)
    full_name = str(repo.get("full_name") or "")
    url = str(repo.get("html_url") or (f"https://github.com/{full_name}" if full_name else ""))
    if current is None:
        state.nonpublic[key] = NonPublicHit(
            repository_id=int(repo["id"]),
            repository_full_name=full_name,
            repository_url=url,
            discovery_queries=list(query_ids),
            reason=reason,
        )
    else:
        for query_id in query_ids:
            if query_id not in current.discovery_queries:
                current.discovery_queries.append(query_id)
    state.candidates.pop(key, None)


def _hydrate(state: DiscoveryState, client, *, log: logging.Logger) -> None:
    for key, candidate in list(state.candidates.items()):
        if candidate.hydration_status == "ok" or candidate.hydration_status == "not_found":
            continue
        try:
            payload = client.get_repository(candidate.repository_full_name)
        except GitHubRequestError as exc:
            if exc.status == 404:
                candidate.hydration_status = "not_found"
                log.warning("repository not found during hydration: %s", candidate.repository_full_name)
            else:
                candidate.hydration_status = "error"
                log.warning("hydration failed for %s: %s", candidate.repository_full_name, exc.message)
            continue
        except GitHubAuthError:
            raise
        if not isinstance(payload, dict):
            candidate.hydration_status = "error"
            continue
        if not _looks_public(payload):
            _merge_nonpublic(state, payload, list(candidate.discovery_queries), "not_public")
            continue
        _apply_repository_payload(candidate, payload)
        candidate.hydration_status = "ok"


def _apply_repository_payload(candidate: Candidate, payload: dict) -> None:
    candidate.repository_full_name = str(payload.get("full_name") or candidate.repository_full_name)
    candidate.repository_url = str(payload.get("html_url") or candidate.repository_url)
    candidate.default_branch = str(payload.get("default_branch") or "")
    if isinstance(payload.get("fork"), bool):
        candidate.is_fork = payload["fork"]
    if isinstance(payload.get("archived"), bool):
        candidate.archived = payload["archived"]
    if isinstance(payload.get("stargazers_count"), int):
        candidate.stars = payload["stargazers_count"]
    candidate.license = _license_name(payload)
    candidate.created_at = str(payload.get("created_at") or "")
    candidate.updated_at = str(payload.get("updated_at") or "")
    candidate.pushed_at = str(payload.get("pushed_at") or "")
    parent = payload.get("parent") if isinstance(payload.get("parent"), dict) else {}
    if candidate.is_fork and parent:
        if parent.get("id") is not None:
            candidate.parent_repository_id = int(parent["id"])
        candidate.parent_repository_full_name = str(parent.get("full_name") or "")
    else:
        candidate.parent_repository_id = None
        candidate.parent_repository_full_name = ""


def _looks_public(repo: dict) -> bool:
    if repo.get("private") is True:
        return False
    visibility = repo.get("visibility")
    if isinstance(visibility, str) and visibility != "public":
        return False
    return True


def _license_name(repo: dict) -> str:
    license_info = repo.get("license")
    if not isinstance(license_info, dict):
        return ""
    spdx = license_info.get("spdx_id")
    if isinstance(spdx, str) and spdx:
        return spdx
    name = license_info.get("name")
    return name if isinstance(name, str) else ""


def _date_children(query: PlannedQuery, window_start: date, window_end: date) -> list[PlannedQuery]:
    start = date.fromisoformat(query.created_start) if query.created_start else window_start
    end = date.fromisoformat(query.created_end) if query.created_end else window_end
    halves = split_created_range(start, end)
    if halves is None:
        return []
    return [_with_created_range(query, half[0], half[1]) for half in halves]


def _with_created_range(query: PlannedQuery, start: date, end: date) -> PlannedQuery:
    created = (start, end)
    base_text = " ".join(part for part in query.query_text.split() if not part.startswith("created:"))
    text = f"{base_text} created:{start.isoformat()}..{end.isoformat()}"
    created_label = f"created:{start.isoformat()}..{end.isoformat()}"
    partition_parts = [part for part in query.partition.split(";") if part and not part.startswith("created:")]
    partition_parts.append(created_label)
    return PlannedQuery(
        query_id=_query_id("repository", query.base_id, None, created),
        base_id=query.base_id,
        query_family=query.query_family,
        endpoint="repository",
        query_text=text,
        partition=";".join(partition_parts),
        allow_date_partition=True,
        created_start=start.isoformat(),
        created_end=end.isoformat(),
    )


def _provenance(query: PlannedQuery) -> str:
    if query.fork_stream:
        return f"{query.endpoint}:{query.query_family}:{query.fork_stream}"
    return f"{query.endpoint}:{query.query_family}"


def _planned(
    *,
    endpoint: str,
    base_id: str,
    family: str,
    term: str,
    extension: str | None,
    fork_qualifier: str | None,
    allow_date_partition: bool,
    fork_stream: str = "",
    content_qualifier: str | None = None,
    public_qualifier: str | None = None,
) -> PlannedQuery:
    parts = [term]
    if content_qualifier:
        parts.append(content_qualifier)
    if public_qualifier:
        parts.append(public_qualifier)
    if fork_qualifier:
        parts.append(fork_qualifier)
    if extension:
        parts.append(f"extension:{extension}")
    partition_parts = []
    if fork_stream:
        partition_parts.append(f"stream:{fork_stream}")
    if fork_qualifier:
        partition_parts.append(fork_qualifier)
    if extension:
        partition_parts.append(f"extension:{extension}")
    return PlannedQuery(
        query_id=_query_id(endpoint, base_id, extension, None, fork_stream or None),
        base_id=base_id,
        query_family=family,
        endpoint=endpoint,  # type: ignore[arg-type]
        query_text=" ".join(parts),
        partition=";".join(partition_parts),
        fork_stream=fork_stream,
        allow_date_partition=allow_date_partition,
    )


def _query_id(
    endpoint: str,
    base_id: str,
    extension: str | None,
    created: tuple[date, date] | None,
    fork_stream: str | None = None,
) -> str:
    parts = [endpoint, base_id]
    if fork_stream:
        parts.append(fork_stream)
    if extension:
        parts.append(f"ext_{extension}")
    if created:
        parts.append(f"created_{created[0].isoformat()}_{created[1].isoformat()}")
    return "__".join(parts)


def _pages_needed(total_count: int, per_page: int) -> int:
    if total_count <= 0:
        return 1
    retrievable = min(total_count, RESULT_CEILING)
    max_pages = ceil(RESULT_CEILING / per_page)
    return min(max_pages, ceil(retrievable / per_page))


def _record_execution(
    state: DiscoveryState,
    query: PlannedQuery,
    *,
    clock: Callable[[], datetime],
    result_count: int | None,
    pages: int,
    incomplete: bool | None,
    truncated: bool,
    reason: str,
    status: str,
) -> None:
    state.executions[query.query_id] = QueryExecution(
        query_id=query.query_id,
        query_family=query.query_family,
        endpoint=query.endpoint,
        query_text=query.query_text,
        partition=query.partition,
        executed_at=_stamp(clock),
        result_count_reported=result_count,
        pages_retrieved=pages,
        incomplete_results=incomplete,
        potentially_truncated=truncated,
        truncation_reason=reason,
        api_status=status,
    )


def _stamp(clock: Callable[[], datetime]) -> str:
    moment = clock()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _persist(state: DiscoveryState, data_dir: Path) -> None:
    save_state(state_path(data_dir), state)
    export_results(state, data_dir / "results")


def format_plan(planned: list[PlannedQuery]) -> str:
    lines = ["query_id\tendpoint\tfamily\tpartition\tquery_text"]
    for item in planned:
        lines.append(
            "\t".join([item.query_id, item.endpoint, item.query_family, item.partition, item.query_text])
        )
    code = sum(1 for item in planned if item.endpoint == "code")
    repository = sum(1 for item in planned if item.endpoint == "repository")
    lines.append(f"# planned={len(planned)} code={code} repository={repository}")
    lines.append("# date partitions are created at runtime only if a repository query hits the 1000-result ceiling")
    return "\n".join(lines) + "\n"
