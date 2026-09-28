#!/usr/bin/env python3
"""SRC006 ODCT adapter.

Fixed snapshot: Zenodo record DOI 10.5281/zenodo.19222588.

Collects qualifying artifacts from the exact persistent record.
Excludes the demonstration video as out of current protocol scope.
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import quote

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from pilot_common import (
    UNKNOWN,
    AdapterResult,
    Candidate,
    existing_artifact_urls,
    fail,
    guess_format_from_name,
    http_get_json,
    mark_already_recorded,
    run_adapter,
)

ODCT_DOI = "10.5281/zenodo.19222588"
ODCT_API_URL = "https://zenodo.org/api/records/19222588"
ODCT_EXCLUDE_FILES = {"Demo_Video_ODCT.mp4"}
ODCT_REQUIRED_FILES = {
    "saref_and_saref4ener_shacl_shape.ttl",
    "compliant_dataset.json",
    "details_description_of_shacl_shape.md",
}


def classify_odct_file(filename: str) -> tuple[str, str]:
    lower = filename.lower()
    if lower.endswith(".md"):
        return "documentation", "markdown"
    if "report" in lower and lower.endswith(".pdf"):
        return "documentation", "pdf"
    if lower.endswith("_shacl_shape.ttl") or lower.endswith(".ttl"):
        return "shacl", "turtle"
    if "modifieddataset" in lower:
        return "test_data", "json"
    if "compliant_dataset" in lower:
        return "example_data", "json"
    return UNKNOWN, guess_format_from_name(filename)


def collect() -> AdapterResult:
    record = http_get_json(ODCT_API_URL)
    files = record.get("files")
    if not isinstance(files, list) or not files:
        fail("ODCT Zenodo record has no files list")

    doi = record.get("doi") or record.get("metadata", {}).get("doi") or ODCT_DOI
    candidates: list[Candidate] = []
    found_names: set[str] = set()
    warnings: list[str] = []

    for item in files:
        if not isinstance(item, dict):
            fail("ODCT Zenodo files entry is not an object")
        key = str(item.get("key") or "")
        if not key:
            fail("ODCT Zenodo file missing key")
        found_names.add(key)
        if key in ODCT_EXCLUDE_FILES:
            warnings.append(f"ODCT skipped out-of-scope file: {key}")
            continue

        artifact_type, fmt = classify_odct_file(key)
        checksum = str(item.get("checksum") or "")
        links = item.get("links") if isinstance(item.get("links"), dict) else {}
        url = str(links.get("content") or links.get("download") or "")
        if not url:
            url = (
                "https://zenodo.org/api/records/19222588/files/"
                f"{quote(key)}/content"
            )

        intended = UNKNOWN
        if artifact_type == "shacl":
            intended = "SAREF and SAREF4ENER"
        elif artifact_type in {"example_data", "test_data"}:
            intended = "ODCT validation datasets for SAREF/SAREF4ENER shapes"

        candidates.append(
            Candidate(
                source_id="SRC006",
                artifact_type=artifact_type,
                name=key,
                version=str(record.get("metadata", {}).get("version") or UNKNOWN),
                url=url,
                repository_path="",
                commit_or_release=doi,
                format=fmt,
                authoritative_status="research",
                intended_target=intended,
                generation_method=UNKNOWN,
                examples_available="yes",
                tests_available="yes",
                license=UNKNOWN,
                notes=f"checksum={checksum}" if checksum else "",
                source_snapshot=f"Zenodo record {doi}",
                evidence_url=f"https://doi.org/{doi}",
                collection_note=(
                    "enumerated from exact Zenodo record; demo video excluded"
                ),
            )
        )

    missing = sorted(ODCT_REQUIRED_FILES - found_names)
    if missing:
        fail(f"ODCT Zenodo record missing expected files: {', '.join(missing)}")

    mark_already_recorded(candidates, existing_artifact_urls())
    return AdapterResult(
        source_id="SRC006",
        source_name="ODCT",
        status="processed",
        candidates=candidates,
        warnings=warnings,
        notes=[
            "Research source using SAREF/SAREF4ENER; kept separate from SRC001 SAREF."
        ],
    )


def main() -> int:
    run_adapter(collect(), slug="odct")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
