#!/usr/bin/env python3
"""SRC002 QUDT adapter.

Fixed snapshot: QUDT 3.5.2.
Existing artifacts.csv rows are inspected and reported without duplication.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from pilot_common import (
    ARTIFACTS_PATH,
    RETRIEVED_ON,
    UNKNOWN,
    AdapterResult,
    Candidate,
    existing_artifact_urls,
    fail,
    load_csv,
    mark_already_recorded,
    run_adapter,
)


def collect() -> AdapterResult:
    rows = [
        row for row in load_csv(ARTIFACTS_PATH) if row.get("source_id") == "SRC002"
    ]
    if not rows:
        fail("QUDT adapter expected existing SRC002 rows in artifacts.csv")

    candidates: list[Candidate] = []
    for row in rows:
        url = row.get("url", "").strip()
        if not url:
            fail(f"QUDT existing artifact {row.get('artifact_id')} has empty url")
        candidates.append(
            Candidate(
                source_id="SRC002",
                artifact_type=row.get("artifact_type") or UNKNOWN,
                name=row.get("name") or UNKNOWN,
                version=row.get("version") or "3.5.2",
                url=url,
                repository_path=row.get("repository_path", ""),
                commit_or_release=row.get("commit_or_release") or "3.5.2",
                retrieved_on=row.get("retrieved_on") or RETRIEVED_ON,
                format=row.get("format") or UNKNOWN,
                authoritative_status=row.get("authoritative_status") or UNKNOWN,
                intended_target=row.get("intended_target") or UNKNOWN,
                profile_name=row.get("profile_name", ""),
                generation_method=row.get("generation_method") or UNKNOWN,
                examples_available=row.get("examples_available") or UNKNOWN,
                tests_available=row.get("tests_available") or UNKNOWN,
                license=row.get("license") or UNKNOWN,
                local_path=row.get("local_path", ""),
                notes=row.get("notes", ""),
                source_snapshot="QUDT 3.5.2",
                evidence_url="https://www.qudt.org/",
                collection_note=(
                    f"already recorded in artifacts.csv as {row.get('artifact_id')}"
                ),
            )
        )

    mark_already_recorded(candidates, existing_artifact_urls())
    return AdapterResult(
        source_id="SRC002",
        source_name="QUDT",
        status="processed",
        candidates=candidates,
        notes=["Fixed snapshot QUDT 3.5.2 already represented in artifacts.csv."],
    )


def main() -> int:
    run_adapter(collect(), slug="qudt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
