#!/usr/bin/env python3
"""Enumerate SHACL-bearing OGC Building Blocks from a fixed register snapshot.

Reads register.json from one pinned repository commit and writes a reviewable
CSV report. Does not modify data/artifacts.csv.
"""

from __future__ import annotations

import csv
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "reports" / "ogc_building_blocks_shacl.csv"

REPO = "https://github.com/opengeospatial/bblocks"
COMMIT = "af182cbb1a49775a3ecd526bed20a2600ab3e639"
REGISTER_URL = (
    f"https://raw.githubusercontent.com/opengeospatial/bblocks/{COMMIT}/register.json"
)

FIELDNAMES = [
    "itemIdentifier",
    "name",
    "version",
    "status",
    "maturity",
    "scope",
    "group",
    "shacl_urls",
    "sourceFiles",
    "validationPassed",
    "testOutputs",
    "source_references",
]


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def fetch_register(url: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        fail(f"could not retrieve register.json from {url}: {exc}")

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        fail(f"register.json is not valid JSON: {exc}")

    if not isinstance(data, dict):
        fail("expected register.json to contain a JSON object")
    return data


def load_register(path: Path | None) -> dict[str, Any]:
    if path is not None:
        if not path.exists():
            fail(f"register file not found: {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fail(f"register file is not valid JSON: {exc}")
        if not isinstance(data, dict):
            fail("expected register file to contain a JSON object")
        return data
    return fetch_register(REGISTER_URL)


def shacl_urls_from_field(shacl_shapes: Any) -> list[str]:
    """Return SHACL URLs in first-seen order. Empty list means non-qualifying."""
    if shacl_shapes is None:
        return []
    if isinstance(shacl_shapes, str):
        return [] if is_blank(shacl_shapes) else [shacl_shapes.strip()]
    if isinstance(shacl_shapes, list):
        urls: list[str] = []
        for item in shacl_shapes:
            if isinstance(item, str) and not is_blank(item):
                urls.append(item.strip())
        return urls
    if isinstance(shacl_shapes, dict):
        urls = []
        seen: set[str] = set()
        for value in shacl_shapes.values():
            if isinstance(value, str) and not is_blank(value):
                url = value.strip()
                if url not in seen:
                    seen.add(url)
                    urls.append(url)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and not is_blank(item):
                        url = item.strip()
                        if url not in seen:
                            seen.add(url)
                            urls.append(url)
        return urls
    fail(
        "unexpected shaclShapes type "
        f"{type(shacl_shapes).__name__}; expected object, list, string, or null"
    )


def format_source_references(sources: Any) -> str:
    if sources is None:
        return ""
    if not isinstance(sources, list):
        return as_text(sources)

    parts: list[str] = []
    for item in sources:
        if not isinstance(item, dict):
            parts.append(as_text(item))
            continue
        title = as_text(item.get("title")).strip()
        link = as_text(item.get("link")).strip()
        if title and link:
            parts.append(f"{title} <{link}>")
        elif title:
            parts.append(title)
        elif link:
            parts.append(link)
    return " | ".join(parts)


def extract_rows(register: dict[str, Any]) -> tuple[list[dict[str, str]], int]:
    if "bblocks" not in register:
        fail("register.json is missing required key 'bblocks'")

    bblocks = register["bblocks"]
    if not isinstance(bblocks, list):
        fail("register.json key 'bblocks' must be an array")

    rows: list[dict[str, str]] = []
    for index, entry in enumerate(bblocks):
        if not isinstance(entry, dict):
            fail(f"bblocks[{index}] is not an object")

        urls = shacl_urls_from_field(entry.get("shaclShapes"))
        if not urls:
            continue

        item_id = as_text(entry.get("itemIdentifier")).strip()
        if not item_id:
            fail(f"bblocks[{index}] has non-empty shaclShapes but no itemIdentifier")

        rows.append(
            {
                "itemIdentifier": item_id,
                "name": as_text(entry.get("name")),
                "version": as_text(entry.get("version")),
                "status": as_text(entry.get("status")),
                "maturity": as_text(entry.get("maturity")),
                "scope": as_text(entry.get("scope")),
                "group": as_text(entry.get("group")),
                "shacl_urls": " | ".join(urls),
                "sourceFiles": as_text(entry.get("sourceFiles")),
                "validationPassed": as_text(entry.get("validationPassed")),
                "testOutputs": as_text(entry.get("testOutputs")),
                "source_references": format_source_references(entry.get("sources")),
            }
        )

    rows.sort(key=lambda row: row["itemIdentifier"])
    return rows, len(bblocks)


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def count_distinct_shacl_urls(rows: list[dict[str, str]]) -> int:
    urls: set[str] = set()
    for row in rows:
        for url in row["shacl_urls"].split(" | "):
            if url:
                urls.add(url)
    return len(urls)


def main(argv: list[str]) -> int:
    register_path: Path | None = None
    if len(argv) == 2:
        register_path = Path(argv[1])
    elif len(argv) > 2:
        fail(f"usage: {Path(argv[0]).name} [path/to/register.json]")

    print(f"Repository: {REPO}")
    print(f"Commit:     {COMMIT}")
    if register_path is None:
        print(f"Register:   {REGISTER_URL}")
    else:
        print(f"Register:   {register_path}")

    register = load_register(register_path)
    rows, total_blocks = extract_rows(register)
    write_csv(OUTPUT_PATH, rows)

    distinct_urls = count_distinct_shacl_urls(rows)
    print()
    print(f"Total building blocks in register:     {total_blocks}")
    print(f"Building blocks with shaclShapes:      {len(rows)}")
    print(f"Distinct SHACL artifact URLs:          {distinct_urls}")
    print(f"Wrote: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
