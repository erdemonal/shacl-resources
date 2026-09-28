#!/usr/bin/env python3
"""Promote reviewed pilot candidates into data/artifacts.csv.

Deterministic, offline, and auditable. Does not access the web, discover
sources, or reinterpret metadata.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from validate_manifest import ALLOWED_ARTIFACT_TYPES, ARTIFACT_COLUMNS

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCES_PATH = REPO_ROOT / "data" / "sources.csv"
ARTIFACTS_PATH = REPO_ROOT / "data" / "artifacts.csv"
CANDIDATES_PATH = REPO_ROOT / "reports" / "pilot_artifact_candidates.csv"
SUMMARY_PATH = REPO_ROOT / "reports" / "pilot_promotion_summary.json"

EXPECTED_CANONICAL_BEFORE = 7
EXPECTED_CANDIDATES = 38
EXPECTED_DUPLICATES = 7
EXPECTED_NEW = 31
EXPECTED_CANONICAL_AFTER = 38

CANONICAL_FIELD_SET = set(ARTIFACT_COLUMNS)
CANDIDATE_ONLY_FIELDS = ("notes", "source_snapshot", "evidence_url", "collection_note")


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        fail(f"missing file: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def normalize_url(url: str) -> str:
    return url.strip()


def build_notes(candidate: dict[str, str]) -> str:
    parts: list[str] = []
    existing_notes = (candidate.get("notes") or "").strip()
    if existing_notes:
        parts.append(existing_notes)

    snapshot = (candidate.get("source_snapshot") or "").strip()
    if snapshot:
        parts.append(f"Source snapshot: {snapshot}")

    evidence = (candidate.get("evidence_url") or "").strip()
    if evidence:
        parts.append(f"Evidence: {evidence}")

    collection_note = (candidate.get("collection_note") or "").strip()
    if collection_note:
        parts.append(f"Collection note: {collection_note}")

    return "\n".join(parts)


def candidate_to_canonical(candidate: dict[str, str], artifact_id: str) -> dict[str, str]:
    row = {column: "" for column in ARTIFACT_COLUMNS}
    row["artifact_id"] = artifact_id
    for column in ARTIFACT_COLUMNS:
        if column == "artifact_id":
            continue
        if column == "notes":
            row["notes"] = build_notes(candidate)
            continue
        if column in candidate:
            row[column] = candidate.get(column) or ""
    return row


def write_artifacts(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ARTIFACT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    sources = load_csv(SOURCES_PATH)
    artifacts = load_csv(ARTIFACTS_PATH)
    candidates = load_csv(CANDIDATES_PATH)

    if len(artifacts) != EXPECTED_CANONICAL_BEFORE:
        fail(
            f"expected {EXPECTED_CANONICAL_BEFORE} canonical artifacts before "
            f"promotion; found {len(artifacts)}"
        )
    if len(candidates) != EXPECTED_CANDIDATES:
        fail(
            f"expected {EXPECTED_CANDIDATES} candidate rows; found {len(candidates)}"
        )

    source_by_id = {row.get("source_id", ""): row for row in sources}
    existing_ids = [row.get("artifact_id", "") for row in artifacts]
    if existing_ids != [f"ART{i:03d}" for i in range(1, 8)]:
        fail(f"unexpected existing artifact IDs: {existing_ids}")

    existing_urls: dict[str, str] = {}
    for row in artifacts:
        url = normalize_url(row.get("url", ""))
        if not url:
            fail(f"canonical artifact {row.get('artifact_id')} has empty URL")
        if url in existing_urls:
            fail(f"duplicate URL already present in artifacts.csv: {url}")
        existing_urls[url] = row.get("artifact_id", "")

    new_candidates: list[dict[str, str]] = []
    duplicates_skipped = 0

    for index, candidate in enumerate(candidates, start=2):
        source_id = (candidate.get("source_id") or "").strip()
        artifact_type = (candidate.get("artifact_type") or "").strip()
        url = normalize_url(candidate.get("url", ""))

        if not source_id:
            fail(f"candidates.csv:{index}: missing source_id")
        if source_id not in source_by_id:
            fail(f"candidates.csv:{index}: unknown source_id {source_id!r}")
        if source_id == "SRC001":
            fail("SRC001 SAREF must contribute no candidate artifacts")

        decision = (source_by_id[source_id].get("screening_decision") or "").strip()
        if decision != "included":
            fail(
                f"candidates.csv:{index}: source {source_id} is not included "
                f"(screening_decision={decision!r})"
            )

        if artifact_type not in ALLOWED_ARTIFACT_TYPES:
            fail(
                f"candidates.csv:{index}: artifact_type {artifact_type!r} is not "
                "allowed by validate_manifest.py"
            )
        if not url:
            fail(f"candidates.csv:{index}: missing url")

        if url in existing_urls:
            duplicates_skipped += 1
            continue

        new_candidates.append(candidate)

    if duplicates_skipped != EXPECTED_DUPLICATES:
        fail(
            f"expected {EXPECTED_DUPLICATES} duplicate URLs skipped; "
            f"found {duplicates_skipped}"
        )
    if len(new_candidates) != EXPECTED_NEW:
        fail(
            f"expected {EXPECTED_NEW} new artifacts to promote; "
            f"found {len(new_candidates)}"
        )

    new_candidates.sort(
        key=lambda row: (
            row.get("source_id", ""),
            row.get("artifact_type", ""),
            normalize_url(row.get("url", "")),
        )
    )

    promoted_rows: list[dict[str, str]] = []
    next_id = 8
    for candidate in new_candidates:
        artifact_id = f"ART{next_id:03d}"
        next_id += 1
        promoted_rows.append(candidate_to_canonical(candidate, artifact_id))

    merged = list(artifacts) + promoted_rows
    if len(merged) != EXPECTED_CANONICAL_AFTER:
        fail(
            f"expected {EXPECTED_CANONICAL_AFTER} canonical rows after promotion; "
            f"found {len(merged)}"
        )

    merged_urls = [normalize_url(row.get("url", "")) for row in merged]
    if len(merged_urls) != len(set(merged_urls)):
        fail("URL uniqueness check failed after merge")

    # Ensure we never wrote candidate-only columns into the canonical CSV schema.
    for row in promoted_rows:
        unexpected = set(row) - CANONICAL_FIELD_SET
        if unexpected:
            fail(f"unexpected canonical fields: {sorted(unexpected)}")

    write_artifacts(ARTIFACTS_PATH, merged)

    per_source = Counter(row["source_id"] for row in promoted_rows)
    per_type = Counter(row["artifact_type"] for row in promoted_rows)
    summary = {
        "canonical_rows_before": EXPECTED_CANONICAL_BEFORE,
        "candidate_rows_reviewed": EXPECTED_CANDIDATES,
        "duplicates_skipped": duplicates_skipped,
        "new_rows_promoted": len(promoted_rows),
        "canonical_rows_after": len(merged),
        "promoted_count_per_source": dict(sorted(per_source.items())),
        "promoted_count_per_artifact_type": dict(sorted(per_type.items())),
        "existing_artifact_ids_preserved": existing_ids,
        "new_artifact_id_range": (
            [promoted_rows[0]["artifact_id"], promoted_rows[-1]["artifact_id"]]
            if promoted_rows
            else []
        ),
        "candidate_only_fields_folded_into_notes": list(CANDIDATE_ONLY_FIELDS),
        "output": str(ARTIFACTS_PATH.relative_to(REPO_ROOT)),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print("=== Pilot promotion summary ===")
    print(f"canonical rows before:   {summary['canonical_rows_before']}")
    print(f"candidate rows reviewed: {summary['candidate_rows_reviewed']}")
    print(f"duplicates skipped:      {summary['duplicates_skipped']}")
    print(f"new rows promoted:       {summary['new_rows_promoted']}")
    print(f"canonical rows after:    {summary['canonical_rows_after']}")
    print("promoted per source:")
    for source_id, count in summary["promoted_count_per_source"].items():
        print(f"  - {source_id}: {count}")
    print("promoted per artifact type:")
    for artifact_type, count in summary["promoted_count_per_artifact_type"].items():
        print(f"  - {artifact_type}: {count}")
    print(f"wrote: {ARTIFACTS_PATH.relative_to(REPO_ROOT)}")
    print(f"wrote: {SUMMARY_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
