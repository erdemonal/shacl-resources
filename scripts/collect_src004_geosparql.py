#!/usr/bin/env python3
"""SRC004 GeoSPARQL adapter.

Fixed snapshot: GeoSPARQL 1.1 validator pinned to
opengeospatial/geosemantics-semantic-resources commit
658d2ad16e4c28a786ff657a8517fa8f7c50abe7

Collects only the official informative SHACL validator and the minimum
specification document. Community extended shapes are noted for later
screening, not collected as pilot artifacts.
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
    require_url,
    run_adapter,
)

GEOSPARQL_COMMIT = "658d2ad16e4c28a786ff657a8517fa8f7c50abe7"
GEOSPARQL_VALIDATOR_PATH = (
    "resources/geosparql-swg/geosparql-1.1/validators/geo-validator.ttl"
)
GEOSPARQL_VALIDATOR_URL = (
    "https://raw.githubusercontent.com/opengeospatial/"
    f"geosemantics-semantic-resources/{GEOSPARQL_COMMIT}/"
    f"{GEOSPARQL_VALIDATOR_PATH}"
)
GEOSPARQL_VALIDATOR_IRI = "http://www.opengis.net/def/geosparql/validator"
GEOSPARQL_SPEC_URL = "https://docs.ogc.org/is/22-047r1/22-047r1.html"
GEOSPARQL_EXTENDED_REPO = "https://github.com/opengeospatial/ogc-geosparql-shapes"


def collect() -> AdapterResult:
    require_url(GEOSPARQL_VALIDATOR_URL, "GeoSPARQL 1.1 validator")
    require_url(GEOSPARQL_SPEC_URL, "GeoSPARQL 1.1 specification")

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
            repository_path=GEOSPARQL_VALIDATOR_PATH,
            commit_or_release=GEOSPARQL_COMMIT,
            format="turtle",
            authoritative_status=UNKNOWN,
            intended_target="GeoSPARQL 1.1 RDF data",
            generation_method=UNKNOWN,
            examples_available=UNKNOWN,
            tests_available=UNKNOWN,
            license=UNKNOWN,
            notes=(
                f"Canonical IRI: {GEOSPARQL_VALIDATOR_IRI}. "
                "As of GeoSPARQL 1.1 this validator is informative, not normative."
            ),
            source_snapshot=(
                f"geosemantics-semantic-resources@{GEOSPARQL_COMMIT} / GeoSPARQL 1.1"
            ),
            evidence_url=GEOSPARQL_SPEC_URL,
            collection_note=(
                "official core validator pinned to exact repository commit; "
                "informative status recorded"
            ),
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
    ]

    mark_already_recorded(candidates, existing_artifact_urls())
    return AdapterResult(
        source_id="SRC004",
        source_name="GeoSPARQL",
        status="processed",
        candidates=candidates,
        warnings=[
            "Community repository "
            f"{GEOSPARQL_EXTENDED_REPO} was observed but not collected as a "
            "pilot artifact; it is a repository of extended community shapes, "
            "not a specific official GeoSPARQL 1.1 SHACL resource. "
            "It may be screened later as a separate source."
        ],
        notes=[
            "Validator URL is pinned to an exact repository commit, not main.",
        ],
    )


def main() -> int:
    run_adapter(collect(), slug="geosparql")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
