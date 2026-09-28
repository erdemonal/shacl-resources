#!/usr/bin/env python3
"""Orchestrate per-source pilot collectors and merge reviewable outputs.

This script does not contain source-specific collection rules.
Each screened source has its own adapter script under scripts/.

Workflow:
  collect_src00X_*.py  -> reports/candidates/
  collect_pilot_artifacts.py -> merged candidates + summary

Does not modify data/artifacts.csv.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import collect_src001_saref
import collect_src002_qudt
import collect_src003_ogc_building_blocks
import collect_src004_geosparql
import collect_src005_dcat_ap
import collect_src006_odct
from pilot_common import (
    MERGED_CANDIDATES_PATH,
    MERGED_SUMMARY_PATH,
    REPO_ROOT,
    SOURCES_PATH,
    AdapterResult,
    Candidate,
    fail,
    load_csv,
    normalize_url,
    run_adapter,
    write_candidates,
    write_json,
)

ADAPTERS: list[tuple[str, object]] = [
    ("saref", collect_src001_saref),
    ("qudt", collect_src002_qudt),
    ("ogc_building_blocks", collect_src003_ogc_building_blocks),
    ("geosparql", collect_src004_geosparql),
    ("dcat_ap", collect_src005_dcat_ap),
    ("odct", collect_src006_odct),
]

EXPECTED_SCREENING: dict[str, str] = {
    "SRC001": "candidate",
    "SRC002": "included",
    "SRC003": "included",
    "SRC004": "included",
    "SRC005": "included",
    "SRC006": "included",
}


def validate_screening_decisions(sources: list[dict[str, str]]) -> None:
    by_id = {row.get("source_id", ""): row for row in sources}
    for source_id, expected in EXPECTED_SCREENING.items():
        row = by_id.get(source_id)
        if row is None:
            fail(f"sources.csv missing required pilot source {source_id}")
        actual = (row.get("screening_decision") or "").strip()
        if actual != expected:
            fail(
                f"{source_id} screening_decision must be {expected!r} for this "
                f"pilot collector run; found {actual!r}"
            )


def deduplicate(candidates: list[Candidate]) -> tuple[list[Candidate], int]:
    unique: list[Candidate] = []
    seen: set[str] = set()
    duplicates = 0
    for candidate in candidates:
        key = normalize_url(candidate.url)
        if not key:
            fail(f"candidate without URL: {candidate.name}")
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        unique.append(candidate)
    unique.sort(key=lambda item: (item.source_id, item.artifact_type, item.url))
    return unique, duplicates


def summarize_merged(
    results: list[AdapterResult],
    candidates: list[Candidate],
    duplicates_removed: int,
) -> dict:
    def count_type(artifact_type: str) -> int:
        return sum(1 for item in candidates if item.artifact_type == artifact_type)

    already = sum(
        1
        for item in candidates
        if "already recorded" in item.collection_note
        or "already present in artifacts.csv" in item.collection_note
    )
    warnings: list[str] = []
    for result in results:
        warnings.extend(result.warnings)

    return {
        "sources_considered": [result.source_id for result in results],
        "included_sources_processed": [
            result.source_id for result in results if result.status == "processed"
        ],
        "candidate_sources_skipped": [
            result.source_id for result in results if result.status == "skipped"
        ],
        "candidate_rows": len(candidates),
        "distinct_shacl_artifacts": count_type("shacl"),
        "ontology_vocabulary_artifacts": count_type("ontology"),
        "example_datasets": count_type("example_data"),
        "test_datasets": count_type("test_data"),
        "reports_or_documentation": count_type("documentation")
        + count_type("specification"),
        "duplicates_removed": duplicates_removed,
        "already_in_artifacts_csv": already,
        "warnings": warnings,
        "per_source_outputs": [
            {
                "source_id": result.source_id,
                "source_name": result.source_name,
                "status": result.status,
                "candidate_rows": len(result.candidates),
            }
            for result in results
        ],
        "outputs": {
            "candidates_csv": str(MERGED_CANDIDATES_PATH.relative_to(REPO_ROOT)),
            "summary_json": str(MERGED_SUMMARY_PATH.relative_to(REPO_ROOT)),
            "per_source_dir": "reports/candidates/",
        },
    }


def print_merged_summary(summary: dict) -> None:
    print()
    print("=== Merged pilot collection summary ===")
    print(f"sources considered:              {', '.join(summary['sources_considered'])}")
    print(
        "included sources processed:      "
        f"{', '.join(summary['included_sources_processed'])}"
    )
    print(
        "candidate sources skipped:       "
        f"{', '.join(summary['candidate_sources_skipped']) or '(none)'}"
    )
    print(f"candidate rows:                  {summary['candidate_rows']}")
    print(f"distinct SHACL artifacts:        {summary['distinct_shacl_artifacts']}")
    print(
        "ontology/vocabulary artifacts:   "
        f"{summary['ontology_vocabulary_artifacts']}"
    )
    print(f"example datasets:                {summary['example_datasets']}")
    print(f"test datasets:                   {summary['test_datasets']}")
    print(f"reports/documentation:           {summary['reports_or_documentation']}")
    print(f"duplicates removed:              {summary['duplicates_removed']}")
    print(f"already in artifacts.csv:        {summary['already_in_artifacts_csv']}")
    if summary["warnings"]:
        print("warnings:")
        for warning in summary["warnings"]:
            print(f"  - {warning}")
    print("per-source reports:")
    for item in summary["per_source_outputs"]:
        print(
            f"  - {item['source_id']} {item['source_name']}: "
            f"{item['status']}, {item['candidate_rows']} rows"
        )
    print(f"wrote: {summary['outputs']['candidates_csv']}")
    print(f"wrote: {summary['outputs']['summary_json']}")


def main() -> int:
    if not SOURCES_PATH.exists():
        fail(f"missing {SOURCES_PATH}")

    sources = load_csv(SOURCES_PATH)
    validate_screening_decisions(sources)

    results: list[AdapterResult] = []
    all_candidates: list[Candidate] = []

    for slug, module in ADAPTERS:
        result = run_adapter(module.collect(), slug=slug)
        results.append(result)
        all_candidates.extend(result.candidates)
        print()

    unique, duplicates_removed = deduplicate(all_candidates)
    write_candidates(MERGED_CANDIDATES_PATH, unique)
    summary = summarize_merged(results, unique, duplicates_removed)
    write_json(MERGED_SUMMARY_PATH, summary)
    print_merged_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
