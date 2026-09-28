#!/usr/bin/env python3
"""SRC002 QUDT adapter.

Fixed snapshot: QUDT 3.5.2.

The resource list below is a fixed expected list manually verified against
the official QUDT 3.5.2 catalog. The catalog is the evidence source; this
adapter does not dynamically parse the catalog HTML.
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
    mark_already_recorded,
    require_url,
    run_adapter,
)

CATALOG_URL = "https://www.qudt.org/catalog/qudt-catalog.html"
VERSION = "3.5.2"

# Fixed expected list manually verified against the official QUDT 3.5.2 catalog.
# Aggregate qudt-all distributions are intentionally excluded.
QUDT_RESOURCES: list[dict[str, str]] = [
    {
        "artifact_type": "shacl",
        "name": "QUDT SHACL Schema",
        "url": f"http://qudt.org/{VERSION}/schema/shacl/qudt",
        "intended_target": "QUDT schema",
    },
    {
        "artifact_type": "shacl",
        "name": "QUDT SHACL Datatype Schema",
        "url": f"http://qudt.org/{VERSION}/schema/shacl/datatype",
        "intended_target": "QUDT datatype schema",
    },
    {
        "artifact_type": "shacl",
        "name": "QUDT SHACL Overlay",
        "url": f"http://qudt.org/{VERSION}/schema/shacl/overlay/qudt",
        "intended_target": "QUDT schema",
    },
    {
        "artifact_type": "ontology",
        "name": "QUDT OWL Schema",
        "url": f"http://qudt.org/{VERSION}/schema/qudt",
        "intended_target": "QUDT schema",
    },
    {
        "artifact_type": "ontology",
        "name": "QUDT OWL Datatype Schema",
        "url": f"http://qudt.org/{VERSION}/schema/datatype",
        "intended_target": "QUDT datatype schema",
    },
    {
        "artifact_type": "vocabulary",
        "name": "QUDT Vocabulary Constants",
        "url": f"http://qudt.org/{VERSION}/vocab/constant",
        "intended_target": "QUDT constants vocabulary",
    },
    {
        "artifact_type": "vocabulary",
        "name": "QUDT Vocabulary Datatypes",
        "url": f"http://qudt.org/{VERSION}/vocab/datatype",
        "intended_target": "QUDT datatypes vocabulary",
    },
    {
        "artifact_type": "vocabulary",
        "name": "QUDT Vocabulary Dimension Vectors",
        "url": f"http://qudt.org/{VERSION}/vocab/dimensionvector",
        "intended_target": "QUDT dimension vectors vocabulary",
    },
    {
        "artifact_type": "vocabulary",
        "name": "QUDT Vocabulary Prefixes",
        "url": f"http://qudt.org/{VERSION}/vocab/prefix",
        "intended_target": "QUDT prefixes vocabulary",
    },
    {
        "artifact_type": "vocabulary",
        "name": "QUDT Vocabulary Quantity Kinds",
        "url": f"http://qudt.org/{VERSION}/vocab/quantitykind",
        "intended_target": "QUDT quantity kinds vocabulary",
    },
    {
        "artifact_type": "vocabulary",
        "name": "QUDT Vocabulary Systems of Quantity Kinds",
        "url": f"http://qudt.org/{VERSION}/vocab/soqk",
        "intended_target": "QUDT systems of quantity kinds vocabulary",
    },
    {
        "artifact_type": "vocabulary",
        "name": "QUDT Vocabulary Systems of Units",
        "url": f"http://qudt.org/{VERSION}/vocab/sou",
        "intended_target": "QUDT systems of units vocabulary",
    },
    {
        "artifact_type": "vocabulary",
        "name": "QUDT Vocabulary Units",
        "url": f"http://qudt.org/{VERSION}/vocab/unit",
        "intended_target": "QUDT units vocabulary",
    },
]


def collect() -> AdapterResult:
    require_url(CATALOG_URL, "QUDT catalog")

    candidates: list[Candidate] = []
    for resource in QUDT_RESOURCES:
        url = resource["url"]
        require_url(url, resource["name"])
        candidates.append(
            Candidate(
                source_id="SRC002",
                artifact_type=resource["artifact_type"],
                name=resource["name"],
                version=VERSION,
                url=url,
                commit_or_release=VERSION,
                format="turtle",
                authoritative_status="official",
                intended_target=resource["intended_target"],
                generation_method=UNKNOWN,
                examples_available=UNKNOWN,
                tests_available=UNKNOWN,
                license=UNKNOWN,
                notes=(
                    "Fixed expected resource manually verified against the "
                    "official QUDT 3.5.2 catalog."
                ),
                source_snapshot=f"QUDT {VERSION}",
                evidence_url=CATALOG_URL,
                collection_note=(
                    "verified against official catalog; not dynamically parsed "
                    "from catalog HTML"
                ),
            )
        )

    marked = mark_already_recorded(candidates, existing_artifact_urls())
    return AdapterResult(
        source_id="SRC002",
        source_name="QUDT",
        status="processed",
        candidates=candidates,
        notes=[
            "Resource list is a fixed expected list verified against the official "
            "QUDT 3.5.2 catalog; the catalog is evidence, not an HTML parser input.",
            "Aggregate qudt-all / shacl/qudt-all downloads were not recorded "
            "because they only package graphs already represented individually.",
            f"{marked} candidate URL(s) already present in artifacts.csv.",
        ],
    )


def main() -> int:
    run_adapter(collect(), slug="qudt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
