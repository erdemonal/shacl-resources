#!/usr/bin/env python3
"""SRC005 DCAT-AP adapter.

Fixed snapshot: SEMICeu/DCAT-AP release 3.0.1.

Collects only the dedicated published release SHACL directory:

  releases/3.0.1/shacl/

plus the release index as the minimum documentation artifact.

Does not enumerate releases/3.0.1/html/shacl in this pilot.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from pilot_common import (
    UNKNOWN,
    AdapterResult,
    Candidate,
    existing_artifact_urls,
    fail,
    http_get_json,
    mark_already_recorded,
    require_url,
    run_adapter,
)

DCAT_AP_TAG = "3.0.1"
DCAT_AP_API_SHACL = (
    f"https://api.github.com/repos/SEMICeu/DCAT-AP/contents/"
    f"releases/{DCAT_AP_TAG}/shacl?ref={DCAT_AP_TAG}"
)
EXPECTED_SHACL_FILES = {"dcat-ap-SHACL.ttl", "ranges.ttl"}


def list_ttl_files(api_url: str) -> list[dict[str, Any]]:
    listing = http_get_json(api_url)
    if not isinstance(listing, list):
        fail(f"expected directory listing array from {api_url}")
    files = [
        item
        for item in listing
        if isinstance(item, dict)
        and item.get("type") == "file"
        and str(item.get("name", "")).lower().endswith((".ttl", ".shacl"))
    ]
    if not files:
        fail(f"no Turtle/SHACL files found at {api_url}")
    return files


def collect() -> AdapterResult:
    files = list_ttl_files(DCAT_AP_API_SHACL)
    names = {str(item.get("name") or "") for item in files}
    if names != EXPECTED_SHACL_FILES:
        fail(
            "DCAT-AP 3.0.1 releases/3.0.1/shacl/ contents differ from expected "
            f"{sorted(EXPECTED_SHACL_FILES)}; found {sorted(names)}"
        )

    candidates: list[Candidate] = []
    for item in sorted(files, key=lambda row: str(row.get("name") or "")):
        path = str(item.get("path") or "")
        name = str(item.get("name") or "")
        url = (
            f"https://raw.githubusercontent.com/SEMICeu/DCAT-AP/"
            f"{DCAT_AP_TAG}/{path}"
        )
        require_url(url, name)
        candidates.append(
            Candidate(
                source_id="SRC005",
                artifact_type="shacl",
                name=name,
                version=DCAT_AP_TAG,
                url=url,
                repository_path=path,
                commit_or_release=DCAT_AP_TAG,
                format="turtle",
                authoritative_status=UNKNOWN,
                intended_target="DCAT-AP metadata records",
                profile_name="DCAT-AP",
                generation_method=UNKNOWN,
                examples_available=UNKNOWN,
                tests_available=UNKNOWN,
                license=UNKNOWN,
                notes="Published under the dedicated releases/3.0.1/shacl/ directory.",
                source_snapshot=f"SEMICeu/DCAT-AP release {DCAT_AP_TAG}",
                evidence_url=(
                    f"https://github.com/SEMICeu/DCAT-AP/tree/{DCAT_AP_TAG}/"
                    f"releases/{DCAT_AP_TAG}/shacl"
                ),
                collection_note=(
                    "enumerated only from releases/3.0.1/shacl/; "
                    "html/shacl excluded from this pilot"
                ),
            )
        )

    index_url = (
        f"https://raw.githubusercontent.com/SEMICeu/DCAT-AP/"
        f"{DCAT_AP_TAG}/releases/{DCAT_AP_TAG}/index.html"
    )
    require_url(index_url, "DCAT-AP 3.0.1 release index")
    candidates.append(
        Candidate(
            source_id="SRC005",
            artifact_type="documentation",
            name="DCAT-AP 3.0.1 Release Index",
            version=DCAT_AP_TAG,
            url=index_url,
            repository_path=f"releases/{DCAT_AP_TAG}/index.html",
            commit_or_release=DCAT_AP_TAG,
            format="html",
            authoritative_status=UNKNOWN,
            intended_target="DCAT-AP 3.0.1",
            profile_name="DCAT-AP",
            generation_method=UNKNOWN,
            examples_available=UNKNOWN,
            tests_available=UNKNOWN,
            license=UNKNOWN,
            notes=(
                "Release index retained to identify the selected application "
                "profile snapshot."
            ),
            source_snapshot=f"SEMICeu/DCAT-AP release {DCAT_AP_TAG}",
            evidence_url=(
                f"https://github.com/SEMICeu/DCAT-AP/tree/{DCAT_AP_TAG}/"
                f"releases/{DCAT_AP_TAG}"
            ),
            collection_note="minimum documentation artifact for target identification",
        )
    )

    mark_already_recorded(candidates, existing_artifact_urls())
    return AdapterResult(
        source_id="SRC005",
        source_name="DCAT-AP",
        status="processed",
        candidates=candidates,
        notes=[
            "Pilot selection uses only releases/3.0.1/shacl/ "
            f"({', '.join(sorted(EXPECTED_SHACL_FILES))}).",
            "releases/3.0.1/html/shacl/ is not enumerated here because it "
            "contains supporting HTML/source material, including non-SHACL "
            "import helpers and files that retain 3.0.0 identifiers.",
            "Historical DCAT-AP releases remain outside this pilot snapshot.",
        ],
    )


def main() -> int:
    run_adapter(collect(), slug="dcat_ap")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
