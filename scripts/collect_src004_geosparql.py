#!/usr/bin/env python3
"""SRC004 GeoSPARQL adapter.

Fixed snapshot: GeoSPARQL 1.1.

Collects:
- the official informative SHACL RDF validator;
- the minimum specification document needed to identify target and status;
- the separate community extended-shapes repository as a distinct candidate.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from pilot_common import (
    UNKNOWN,
    AdapterResult,
    Candidate,
    existing_artifact_urls,
    fail,
    http_get_text,
    mark_already_recorded,
    run_adapter,
)

GEOSPARQL_VALIDATOR_URL = (
    "https://raw.githubusercontent.com/opengeospatial/"
    "geosemantics-semantic-resources/main/resources/geosparql-swg/"
    "geosparql-1.1/validators/geo-validator.ttl"
)
GEOSPARQL_VALIDATOR_IRI = "http://www.opengis.net/def/geosparql/validator"
GEOSPARQL_SPEC_URL = "https://docs.ogc.org/is/22-047r1/22-047r1.html"
GEOSPARQL_EXTENDED_REPO = "https://github.com/opengeospatial/ogc-geosparql-shapes"


def collect() -> AdapterResult:
    validator_text = http_get_text(GEOSPARQL_VALIDATOR_URL)
    if "sh:NodeShape" not in validator_text and "sh:PropertyShape" not in validator_text:
        fail("GeoSPARQL validator file does not look like a SHACL shapes graph")
    if "not normative, only informative" not in validator_text:
        fail(
            "GeoSPARQL validator file no longer contains the expected informative "
            "status statement"
        )

    candidates = [
        Candidate(
            source_id="SRC004",
            artifact_type="shacl",
            name="GeoSPARQL 1.1 RDF Shapes Validator",
            version="1.1",
            url=GEOSPARQL_VALIDATOR_URL,
            repository_path=(
                "resources/geosparql-swg/geosparql-1.1/validators/geo-validator.ttl"
            ),
            commit_or_release="GeoSPARQL 1.1",
            format="turtle",
            authoritative_status=UNKNOWN,
            intended_target="GeoSPARQL 1.1 RDF data",
            generation_method=UNKNOWN,
            examples_available=UNKNOWN,
            tests_available=UNKNOWN,
            license="Apache 2.0",
            notes=(
                f"Canonical IRI: {GEOSPARQL_VALIDATOR_IRI}. "
                "As of GeoSPARQL 1.1 this validator is informative, not normative."
            ),
            source_snapshot="GeoSPARQL 1.1 official validator",
            evidence_url=GEOSPARQL_SPEC_URL,
            collection_note="official core validator; informative status recorded",
        ),
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
                "Specification document used to identify the validator target "
                "and status."
            ),
            source_snapshot="GeoSPARQL 1.1",
            evidence_url=GEOSPARQL_SPEC_URL,
            collection_note=(
                "minimum documentation/specification artifact for target identification"
            ),
        ),
        Candidate(
            source_id="SRC004",
            artifact_type="shacl",
            name="GeoSPARQL Extended Shapes Repository",
            version=UNKNOWN,
            url=GEOSPARQL_EXTENDED_REPO,
            commit_or_release=UNKNOWN,
            format=UNKNOWN,
            authoritative_status="community",
            intended_target="GeoSPARQL scenario-specific constraints",
            generation_method=UNKNOWN,
            examples_available=UNKNOWN,
            tests_available=UNKNOWN,
            license=UNKNOWN,
            notes=(
                "Separate community-contributed extended shapes repository. "
                "Not mixed with the official GeoSPARQL 1.1 core validator."
            ),
            source_snapshot="opengeospatial/ogc-geosparql-shapes (community)",
            evidence_url=GEOSPARQL_EXTENDED_REPO,
            collection_note=(
                "reported separately with community status; "
                "not expanded in this pilot pass"
            ),
        ),
    ]

    mark_already_recorded(candidates, existing_artifact_urls())
    return AdapterResult(
        source_id="SRC004",
        source_name="GeoSPARQL",
        status="processed",
        candidates=candidates,
        notes=[
            "Official core validator and community extended shapes are kept separate."
        ],
    )


def main() -> int:
    run_adapter(collect(), slug="geosparql")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
