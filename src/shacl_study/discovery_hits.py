"""Recover file paths from cached Milestone 1 code-search responses.

The discovery run stored GitHub search pages, not a per-file table. Those
cached pages are the only record of which path produced a code-search hit.
"""

from __future__ import annotations

import json
from pathlib import Path


def load_code_search_paths(cache_dir: Path) -> dict[str, list[str]]:
    """Map repository id to the sorted file paths present in cached code-search pages."""
    found: dict[str, set[str]] = {}
    if not cache_dir.is_dir():
        return {}
    for path in cache_dir.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        items = payload.get("items")
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            repository = item.get("repository")
            file_path = item.get("path")
            if not isinstance(repository, dict) or not isinstance(file_path, str) or not file_path:
                continue
            repository_id = repository.get("id")
            if repository_id is None:
                continue
            found.setdefault(str(repository_id), set()).add(file_path)
    return {key: sorted(paths) for key, paths in found.items()}
