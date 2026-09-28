#!/usr/bin/env python3
"""SRC003 OGC Building Blocks adapter.

Fixed snapshot: opengeospatial/bblocks commit
af182cbb1a49775a3ecd526bed20a2600ab3e639

Inspects only the Main register `bblocks` array.
Deduplicates SHACL URLs reused by multiple building blocks.
Does not recursively collect imported external registers.
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
    guess_format_from_name,
    http_get_json,
    mark_already_recorded,
    run_adapter,
)

OGC_COMMIT = "af182cbb1a49775a3ecd526bed20a2600ab3e639"
OGC_REGISTER_URL = (
    f"https://raw.githubusercontent.com/opengeospatial/bblocks/"
    f"{OGC_COMMIT}/register.json"
)


def shacl_urls_from_field(shacl_shapes: Any) -> list[str]:
    if shacl_shapes is None:
        return []
    if isinstance(shacl_shapes, str):
        return [] if not shacl_shapes.strip() else [shacl_shapes.strip()]
    if isinstance(shacl_shapes, list):
        return [
            item.strip()
            for item in shacl_shapes
            if isinstance(item, str) and item.strip()
        ]
    if isinstance(shacl_shapes, dict):
        urls: list[str] = []
        seen: set[str] = set()
        for value in shacl_shapes.values():
            values = value if isinstance(value, list) else [value]
            for item in values:
                if isinstance(item, str) and item.strip() and item.strip() not in seen:
                    seen.add(item.strip())
                    urls.append(item.strip())
        return urls
    fail(f"unexpected shaclShapes type: {type(shacl_shapes).__name__}")


def collect() -> AdapterResult:
    register = http_get_json(OGC_REGISTER_URL)
    if "bblocks" not in register or not isinstance(register["bblocks"], list):
        fail("OGC register.json missing bblocks array")

    url_to_blocks: dict[str, list[str]] = {}
    for index, entry in enumerate(register["bblocks"]):
        if not isinstance(entry, dict):
            fail(f"OGC bblocks[{index}] is not an object")
        item_id = str(entry.get("itemIdentifier") or "").strip()
        for url in shacl_urls_from_field(entry.get("shaclShapes")):
            url_to_blocks.setdefault(url, [])
            if item_id and item_id not in url_to_blocks[url]:
                url_to_blocks[url].append(item_id)

    if not url_to_blocks:
        fail("OGC Main register snapshot unexpectedly has no SHACL URLs")

    candidates: list[Candidate] = []
    for url in sorted(url_to_blocks):
        path = ""
        marker = "/registereditems/"
        if marker in url:
            path = "registereditems/" + url.split(marker, 1)[1]
        referencing = ", ".join(url_to_blocks[url])
        candidates.append(
            Candidate(
                source_id="SRC003",
                artifact_type="shacl",
                name=Path(url).name,
                version=UNKNOWN,
                url=url,
                repository_path=path,
                commit_or_release=OGC_COMMIT,
                format=guess_format_from_name(url),
                authoritative_status=UNKNOWN,
                intended_target="OGC Building Block instance data",
                generation_method=UNKNOWN,
                examples_available="yes",
                tests_available="yes",
                license="Apache 2.0",
                notes=(
                    "Distinct SHACL file referenced by one or more building blocks "
                    "in the fixed OGC Main register snapshot."
                ),
                source_snapshot=(
                    f"opengeospatial/bblocks@{OGC_COMMIT} (Main register bblocks only)"
                ),
                evidence_url=OGC_REGISTER_URL,
                collection_note=f"referenced_by={referencing}",
            )
        )

    mark_already_recorded(candidates, existing_artifact_urls())
    return AdapterResult(
        source_id="SRC003",
        source_name="OGC Building Blocks",
        status="processed",
        candidates=candidates,
        warnings=[
            "OGC adapter inspects only the Main register bblocks array; "
            "imported external registers are not recursively collected."
        ],
        notes=[
            "Artifact unit is the distinct SHACL file URL, not the building block."
        ],
    )


def main() -> int:
    run_adapter(collect(), slug="ogc_building_blocks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
