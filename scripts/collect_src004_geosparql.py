#!/usr/bin/env python3
"""SRC004 GeoSPARQL adapter.

Fixed repository snapshot:
opengeospatial/geosemantics-semantic-resources
commit 658d2ad16e4c28a786ff657a8517fa8f7c50abe7

Primary artifacts are selected from the machine-readable GeoSPARQL 1.1
manifest groups:
  validators/*.ttl
  ontologies/*.ttl
  vocabs/*.ttl
  profiles/geo.ttl

The GeoSPARQL 1.1 standard document is retained as specification evidence.
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
    http_get_text,
    mark_already_recorded,
    require_url,
    run_adapter,
)

GEOSPARQL_COMMIT = "658d2ad16e4c28a786ff657a8517fa8f7c50abe7"
GEOSPARQL_BASE = "resources/geosparql-swg/geosparql-1.1"
GEOSPARQL_MANIFEST_PATH = f"{GEOSPARQL_BASE}/manifest.ttl"
GEOSPARQL_MANIFEST_URL = (
    "https://raw.githubusercontent.com/opengeospatial/"
    f"geosemantics-semantic-resources/{GEOSPARQL_COMMIT}/"
    f"{GEOSPARQL_MANIFEST_PATH}"
)
GEOSPARQL_VALIDATOR_IRI = "http://www.opengis.net/def/geosparql/validator"
GEOSPARQL_SPEC_URL = "https://docs.ogc.org/is/22-047r1/22-047r1.html"
GEOSPARQL_EXTENDED_REPO = "https://github.com/opengeospatial/ogc-geosparql-shapes"
GITHUB_API_BASE = (
    "https://api.github.com/repos/opengeospatial/geosemantics-semantic-resources/"
    f"contents/{GEOSPARQL_BASE}"
)

EXPECTED_MANIFEST_MARKERS = [
    'prof:hasArtifact "validators/*.ttl"',
    'prof:hasArtifact "ontologies/*.ttl"',
    'prof:hasArtifact "vocabs/*.ttl"',
    'prof:hasArtifact "profiles/geo.ttl"',
]


def pinned_raw_url(relative_path: str) -> str:
    return (
        "https://raw.githubusercontent.com/opengeospatial/"
        f"geosemantics-semantic-resources/{GEOSPARQL_COMMIT}/{relative_path}"
    )


def list_ttl_files(subdir: str) -> list[dict[str, Any]]:
    api_url = f"{GITHUB_API_BASE}/{subdir}?ref={GEOSPARQL_COMMIT}"
    listing = http_get_json(api_url)
    if not isinstance(listing, list):
        fail(f"expected directory listing for GeoSPARQL {subdir}")
    files = [
        item
        for item in listing
        if isinstance(item, dict)
        and item.get("type") == "file"
        and str(item.get("name", "")).endswith(".ttl")
    ]
    if not files:
        fail(f"no .ttl files found in GeoSPARQL {subdir}")
    return sorted(files, key=lambda item: str(item.get("name") or ""))


def collect() -> AdapterResult:
    require_url(GEOSPARQL_MANIFEST_URL, "GeoSPARQL 1.1 manifest")
    require_url(GEOSPARQL_SPEC_URL, "GeoSPARQL 1.1 specification")

    manifest_text = http_get_text(GEOSPARQL_MANIFEST_URL)
    for marker in EXPECTED_MANIFEST_MARKERS:
        if marker not in manifest_text:
            fail(f"GeoSPARQL manifest missing expected marker: {marker}")

    candidates: list[Candidate] = []

    for item in list_ttl_files("validators"):
        name = str(item["name"])
        path = str(item["path"])
        url = pinned_raw_url(path)
        require_url(url, name)
        validator_text = http_get_text(url)
        if "not normative, only informative" not in validator_text:
            fail(
                f"GeoSPARQL validator {name} no longer contains the expected "
                "informative status statement"
            )
        candidates.append(
            Candidate(
                source_id="SRC004",
                artifact_type="shacl",
                name=f"GeoSPARQL 1.1 RDF Shapes Validator ({name})",
                version="1.1",
                url=url,
                repository_path=path,
                commit_or_release=GEOSPARQL_COMMIT,
                format="turtle",
                authoritative_status="official",
                intended_target="GeoSPARQL 1.1 RDF data",
                generation_method=UNKNOWN,
                examples_available=UNKNOWN,
                tests_available=UNKNOWN,
                license=UNKNOWN,
                notes=(
                    f"Canonical IRI: {GEOSPARQL_VALIDATOR_IRI}. "
                    "Authoritative provenance is official OGC material, but the "
                    "validator is informative, not normative."
                ),
                source_snapshot=(
                    f"geosemantics-semantic-resources@{GEOSPARQL_COMMIT} / GeoSPARQL 1.1"
                ),
                evidence_url=GEOSPARQL_MANIFEST_URL,
                collection_note="selected via manifest validators/*.ttl",
            )
        )

    for item in list_ttl_files("ontologies"):
        name = str(item["name"])
        path = str(item["path"])
        url = pinned_raw_url(path)
        require_url(url, name)
        candidates.append(
            Candidate(
                source_id="SRC004",
                artifact_type="ontology",
                name=f"GeoSPARQL 1.1 Ontology ({name})",
                version="1.1",
                url=url,
                repository_path=path,
                commit_or_release=GEOSPARQL_COMMIT,
                format="turtle",
                authoritative_status="official",
                intended_target="GeoSPARQL 1.1",
                generation_method=UNKNOWN,
                examples_available=UNKNOWN,
                tests_available=UNKNOWN,
                license=UNKNOWN,
                notes="Primary ontology artifact identified by the GeoSPARQL 1.1 manifest.",
                source_snapshot=(
                    f"geosemantics-semantic-resources@{GEOSPARQL_COMMIT} / GeoSPARQL 1.1"
                ),
                evidence_url=GEOSPARQL_MANIFEST_URL,
                collection_note="selected via manifest ontologies/*.ttl",
            )
        )

    for item in list_ttl_files("vocabs"):
        name = str(item["name"])
        path = str(item["path"])
        url = pinned_raw_url(path)
        require_url(url, name)
        candidates.append(
            Candidate(
                source_id="SRC004",
                artifact_type="vocabulary",
                name=f"GeoSPARQL 1.1 Vocabulary ({name})",
                version="1.1",
                url=url,
                repository_path=path,
                commit_or_release=GEOSPARQL_COMMIT,
                format="turtle",
                authoritative_status="official",
                intended_target="GeoSPARQL 1.1",
                generation_method=UNKNOWN,
                examples_available=UNKNOWN,
                tests_available=UNKNOWN,
                license=UNKNOWN,
                notes="Primary vocabulary artifact identified by the GeoSPARQL 1.1 manifest.",
                source_snapshot=(
                    f"geosemantics-semantic-resources@{GEOSPARQL_COMMIT} / GeoSPARQL 1.1"
                ),
                evidence_url=GEOSPARQL_MANIFEST_URL,
                collection_note="selected via manifest vocabs/*.ttl",
            )
        )

    profile_path = f"{GEOSPARQL_BASE}/profiles/geo.ttl"
    profile_url = pinned_raw_url(profile_path)
    require_url(profile_url, "profiles/geo.ttl")
    candidates.append(
        Candidate(
            source_id="SRC004",
            artifact_type="profile",
            name="GeoSPARQL 1.1 Profile (geo.ttl)",
            version="1.1",
            url=profile_url,
            repository_path=profile_path,
            commit_or_release=GEOSPARQL_COMMIT,
            format="turtle",
            authoritative_status="official",
            intended_target="GeoSPARQL 1.1",
            profile_name="GeoSPARQL",
            generation_method=UNKNOWN,
            examples_available=UNKNOWN,
            tests_available=UNKNOWN,
            license=UNKNOWN,
            notes="Primary profile artifact identified by the GeoSPARQL 1.1 manifest.",
            source_snapshot=(
                f"geosemantics-semantic-resources@{GEOSPARQL_COMMIT} / GeoSPARQL 1.1"
            ),
            evidence_url=GEOSPARQL_MANIFEST_URL,
            collection_note="selected via manifest profiles/geo.ttl",
        )
    )

    candidates.append(
        Candidate(
            source_id="SRC004",
            artifact_type="specification",
            name="OGC GeoSPARQL 1.1 Standard Document",
            version="1.1",
            url=GEOSPARQL_SPEC_URL,
            commit_or_release="OGC 22-047r1 / GeoSPARQL 1.1",
            format="html",
            authoritative_status="official",
            intended_target="GeoSPARQL 1.1",
            generation_method=UNKNOWN,
            examples_available=UNKNOWN,
            tests_available=UNKNOWN,
            license=UNKNOWN,
            notes=(
                "Specification document retained as evidence for the selected "
                "GeoSPARQL 1.1 snapshot and validator status."
            ),
            source_snapshot="GeoSPARQL 1.1",
            evidence_url=GEOSPARQL_SPEC_URL,
            collection_note="specification evidence for target identification",
        )
    )

    mark_already_recorded(candidates, existing_artifact_urls())
    return AdapterResult(
        source_id="SRC004",
        source_name="GeoSPARQL",
        status="processed",
        candidates=candidates,
        warnings=[
            "Community repository "
            f"{GEOSPARQL_EXTENDED_REPO} was observed but not collected as a "
            "pilot artifact; it may be screened later as a separate source."
        ],
        notes=[
            "Primary artifacts enumerated from the fixed GeoSPARQL 1.1 manifest groups.",
            "Root-level catalogue metadata, agents, labels, and root-level "
            "alignments.ttl were not collected as primary artifacts. "
            "ontologies/alignments.ttl remains in scope via ontologies/*.ttl.",
            "Authoritative provenance and normative status are recorded separately "
            "for the SHACL validator.",
        ],
    )


def main() -> int:
    run_adapter(collect(), slug="geosparql")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
