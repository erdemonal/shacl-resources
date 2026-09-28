#!/usr/bin/env python3
"""SRC005 DCAT-AP adapter.

Fixed snapshot: SEMICeu/DCAT-AP release 3.0.1.

Enumerates all SHACL-related Turtle files under the selected release directories.
Does not include historical releases.
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
    run_adapter,
)

DCAT_AP_TAG = "3.0.1"
DCAT_AP_API_SHACL = (
    f"https://api.github.com/repos/SEMICeu/DCAT-AP/contents/"
    f"releases/{DCAT_AP_TAG}/shacl?ref={DCAT_AP_TAG}"
)
DCAT_AP_API_HTML_SHACL = (
    f"https://api.github.com/repos/SEMICeu/DCAT-AP/contents/"
    f"releases/{DCAT_AP_TAG}/html/shacl?ref={DCAT_AP_TAG}"
)


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


def filename_role_note(name: str) -> str:
    lower = name.lower()
    if "recommended" in lower:
        return "filename indicates recommended constraints"
    if lower.startswith("range"):
        return "filename indicates range constraints"
    if "deprecated" in lower:
        return "filename indicates deprecated URI constraints"
    if "import" in lower:
        return "filename indicates imports"
    if "mdr" in lower:
        return "filename indicates MDR vocabulary constraints"
    if "shape" in lower or "shacl" in lower:
        return "filename indicates SHACL shapes"
    return ""


def collect() -> AdapterResult:
    files = list_ttl_files(DCAT_AP_API_SHACL) + list_ttl_files(DCAT_AP_API_HTML_SHACL)

    candidates: list[Candidate] = []
    seen_paths: set[str] = set()
    for item in files:
        path = str(item.get("path") or "")
        name = str(item.get("name") or "")
        if not path or path in seen_paths:
            continue
        seen_paths.add(path)
        url = (
            f"https://raw.githubusercontent.com/SEMICeu/DCAT-AP/"
            f"{DCAT_AP_TAG}/{path}"
        )
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
                examples_available="yes",
                tests_available=UNKNOWN,
                license=UNKNOWN,
                notes=filename_role_note(name),
                source_snapshot=f"SEMICeu/DCAT-AP release {DCAT_AP_TAG}",
                evidence_url=(
                    f"https://github.com/SEMICeu/DCAT-AP/tree/{DCAT_AP_TAG}/"
                    f"releases/{DCAT_AP_TAG}"
                ),
                collection_note="enumerated from fixed 3.0.1 release SHACL directories",
            )
        )

    candidates.append(
        Candidate(
            source_id="SRC005",
            artifact_type="documentation",
            name="DCAT-AP 3.0.1 Release Index",
            version=DCAT_AP_TAG,
            url=(
                f"https://raw.githubusercontent.com/SEMICeu/DCAT-AP/"
                f"{DCAT_AP_TAG}/releases/{DCAT_AP_TAG}/index.html"
            ),
            repository_path=f"releases/{DCAT_AP_TAG}/index.html",
            commit_or_release=DCAT_AP_TAG,
            format="html",
            authoritative_status=UNKNOWN,
            intended_target="DCAT-AP 3.0.1",
            profile_name="DCAT-AP",
            generation_method=UNKNOWN,
            examples_available="yes",
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
        notes=["Historical DCAT-AP releases are outside this pilot snapshot."],
    )


def main() -> int:
    run_adapter(collect(), slug="dcat_ap")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
