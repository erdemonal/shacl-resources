import csv
import json
from pathlib import Path

from shacl_study.models import DiscoveryState

QUERY_COLUMNS = [
    "query_id",
    "query_text",
    "query_family",
    "endpoint",
    "partition",
    "executed_at",
    "result_count_reported",
    "pages_retrieved",
    "incomplete_results",
    "potentially_truncated",
    "truncation_reason",
    "api_status",
]

CANDIDATE_COLUMNS = [
    "repository_id",
    "repository_full_name",
    "repository_url",
    "default_branch",
    "discovered_by",
    "discovery_queries",
    "first_seen_at",
    "last_seen_at",
    "is_fork",
    "parent_repository_id",
    "parent_repository_full_name",
    "archived",
    "stars",
    "license",
    "created_at",
    "updated_at",
    "pushed_at",
]

NONPUBLIC_COLUMNS = [
    "repository_id",
    "repository_full_name",
    "repository_url",
    "discovery_queries",
    "reason",
]


def _cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "|".join(value)
    return str(value)


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _cell(row.get(column)) for column in columns})


def query_rows(state: DiscoveryState) -> list[dict]:
    executions = sorted(
        state.executions.values(),
        key=lambda item: (item.executed_at, item.query_id),
    )
    return [item.model_dump() for item in executions]


def candidate_rows(state: DiscoveryState) -> list[dict]:
    candidates = sorted(
        state.candidates.values(),
        key=lambda item: (item.repository_full_name.lower(), item.repository_id),
    )
    rows = []
    for item in candidates:
        row = item.model_dump()
        row["discovered_by"] = sorted(set(item.discovered_by))
        row["discovery_queries"] = sorted(set(item.discovery_queries))
        rows.append(row)
    return rows


def nonpublic_rows(state: DiscoveryState) -> list[dict]:
    hits = sorted(
        state.nonpublic.values(),
        key=lambda item: (item.repository_full_name.lower(), item.repository_id),
    )
    rows = []
    for item in hits:
        row = item.model_dump()
        row["discovery_queries"] = sorted(set(item.discovery_queries))
        rows.append(row)
    return rows


def export_results(state: DiscoveryState, results_dir: Path) -> None:
    write_csv(results_dir / "discovery_queries.csv", QUERY_COLUMNS, query_rows(state))
    write_csv(results_dir / "candidate_repositories.csv", CANDIDATE_COLUMNS, candidate_rows(state))
    write_csv(results_dir / "nonpublic_hits.csv", NONPUBLIC_COLUMNS, nonpublic_rows(state))


def state_path(data_dir: Path) -> Path:
    return data_dir / "candidates" / "discovery_state.json"


def load_state(path: Path) -> DiscoveryState | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return DiscoveryState.model_validate(payload)


def save_state(path: Path, state: DiscoveryState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(state.model_dump_json(indent=2), encoding="utf-8")


def write_manifest(path: Path, manifest: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
