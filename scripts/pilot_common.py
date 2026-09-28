#!/usr/bin/env python3
"""Shared helpers for pilot artifact collection adapters."""

from __future__ import annotations

import csv
import json
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCES_PATH = REPO_ROOT / "data" / "sources.csv"
ARTIFACTS_PATH = REPO_ROOT / "data" / "artifacts.csv"
CANDIDATES_DIR = REPO_ROOT / "reports" / "candidates"
MERGED_CANDIDATES_PATH = REPO_ROOT / "reports" / "pilot_artifact_candidates.csv"
MERGED_SUMMARY_PATH = REPO_ROOT / "reports" / "pilot_summary.json"

RETRIEVED_ON = "2026-09-28"
UNKNOWN = "unknown"

CANDIDATE_COLUMNS = [
    "source_id",
    "artifact_type",
    "name",
    "version",
    "url",
    "repository_path",
    "commit_or_release",
    "retrieved_on",
    "format",
    "authoritative_status",
    "intended_target",
    "profile_name",
    "generation_method",
    "examples_available",
    "tests_available",
    "license",
    "local_path",
    "notes",
    "source_snapshot",
    "evidence_url",
    "collection_note",
]


@dataclass
class Candidate:
    source_id: str
    artifact_type: str
    name: str
    version: str
    url: str
    repository_path: str = ""
    commit_or_release: str = ""
    retrieved_on: str = RETRIEVED_ON
    format: str = UNKNOWN
    authoritative_status: str = UNKNOWN
    intended_target: str = UNKNOWN
    profile_name: str = ""
    generation_method: str = UNKNOWN
    examples_available: str = UNKNOWN
    tests_available: str = UNKNOWN
    license: str = UNKNOWN
    local_path: str = ""
    notes: str = ""
    source_snapshot: str = ""
    evidence_url: str = ""
    collection_note: str = ""


@dataclass
class AdapterResult:
    source_id: str
    source_name: str
    status: str  # processed | skipped
    candidates: list[Candidate] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def http_get_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "shacl-resources-pilot-collector/0.1"},
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        fail(f"HTTP GET failed for {url}: {exc}")


def http_get_json(url: str) -> Any:
    try:
        return json.loads(http_get_text(url))
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON from {url}: {exc}")


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def normalize_url(url: str) -> str:
    return url.strip()


def guess_format_from_name(name: str) -> str:
    lower = name.lower()
    if lower.endswith((".ttl", ".shacl")):
        return "turtle"
    if lower.endswith((".jsonld", ".json-ld")):
        return "json-ld"
    if lower.endswith(".json"):
        return "json"
    if lower.endswith(".rdf"):
        return "rdfxml"
    if lower.endswith(".md"):
        return "markdown"
    if lower.endswith(".pdf"):
        return "pdf"
    if lower.endswith(".html"):
        return "html"
    return UNKNOWN


def write_candidates(path: Path, candidates: list[Candidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANDIDATE_COLUMNS)
        writer.writeheader()
        for candidate in candidates:
            writer.writerow(asdict(candidate))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def candidate_output_paths(source_id: str, slug: str) -> tuple[Path, Path]:
    csv_path = CANDIDATES_DIR / f"{source_id}_{slug}.csv"
    summary_path = CANDIDATES_DIR / f"{source_id}_{slug}_summary.json"
    return csv_path, summary_path


def summarize_adapter(result: AdapterResult) -> dict[str, Any]:
    def count_type(artifact_type: str) -> int:
        return sum(1 for item in result.candidates if item.artifact_type == artifact_type)

    return {
        "source_id": result.source_id,
        "source_name": result.source_name,
        "status": result.status,
        "candidate_rows": len(result.candidates),
        "distinct_shacl_artifacts": count_type("shacl"),
        "ontology_vocabulary_artifacts": count_type("ontology"),
        "example_datasets": count_type("example_data"),
        "test_datasets": count_type("test_data"),
        "reports_or_documentation": count_type("documentation")
        + count_type("specification"),
        "warnings": result.warnings,
        "notes": result.notes,
    }


def print_adapter_summary(summary: dict[str, Any], csv_path: Path) -> None:
    print(f"=== {summary['source_id']} {summary['source_name']} ===")
    print(f"status:                          {summary['status']}")
    print(f"candidate rows:                  {summary['candidate_rows']}")
    print(f"distinct SHACL artifacts:        {summary['distinct_shacl_artifacts']}")
    print(
        "ontology/vocabulary artifacts:   "
        f"{summary['ontology_vocabulary_artifacts']}"
    )
    print(f"example datasets:                {summary['example_datasets']}")
    print(f"test datasets:                   {summary['test_datasets']}")
    print(f"reports/documentation:           {summary['reports_or_documentation']}")
    if summary["warnings"]:
        print("warnings:")
        for warning in summary["warnings"]:
            print(f"  - {warning}")
    if summary["notes"]:
        print("notes:")
        for note in summary["notes"]:
            print(f"  - {note}")
    print(f"wrote: {csv_path.relative_to(REPO_ROOT)}")


def run_adapter(
    result: AdapterResult,
    slug: str,
) -> AdapterResult:
    csv_path, summary_path = candidate_output_paths(result.source_id, slug)
    write_candidates(csv_path, result.candidates)
    summary = summarize_adapter(result)
    summary["outputs"] = {
        "candidates_csv": str(csv_path.relative_to(REPO_ROOT)),
        "summary_json": str(summary_path.relative_to(REPO_ROOT)),
    }
    write_json(summary_path, summary)
    print_adapter_summary(summary, csv_path)
    return result


def existing_artifact_urls() -> set[str]:
    if not ARTIFACTS_PATH.exists():
        fail(f"missing {ARTIFACTS_PATH}")
    rows = load_csv(ARTIFACTS_PATH)
    return {
        normalize_url(row["url"])
        for row in rows
        if row.get("url", "").strip()
    }


def mark_already_recorded(
    candidates: list[Candidate],
    existing_urls: set[str],
) -> int:
    marked = 0
    for candidate in candidates:
        key = normalize_url(candidate.url)
        if key in existing_urls:
            marked += 1
            if "already recorded" not in candidate.collection_note:
                suffix = "URL already present in artifacts.csv"
                if candidate.collection_note:
                    candidate.collection_note = f"{candidate.collection_note}; {suffix}"
                else:
                    candidate.collection_note = suffix
    return marked
