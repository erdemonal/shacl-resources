#!/usr/bin/env python3
"""Validate sources.csv, artifacts.csv, discovery_log.csv, and discovery_results.csv."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCES_PATH = REPO_ROOT / "data" / "sources.csv"
ARTIFACTS_PATH = REPO_ROOT / "data" / "artifacts.csv"
DISCOVERY_LOG_PATH = REPO_ROOT / "data" / "discovery_log.csv"
DISCOVERY_RESULTS_PATH = REPO_ROOT / "data" / "discovery_results.csv"

SOURCE_COLUMNS = [
    "source_id",
    "name",
    "organization",
    "source_type",
    "homepage",
    "repository",
    "description",
    "discovery_method",
    "discovered_on",
    "screening_decision",
    "exclusion_reason",
    "notes",
]

ARTIFACT_COLUMNS = [
    "artifact_id",
    "source_id",
    "artifact_type",
    "name",
    "version",
    "url",
    "repository_path",
    "commit_or_release",
    "retrieved_on",
    "format",
    "authoritative_status",
    "intended_target",
    "profile_name",
    "generation_method",
    "examples_available",
    "tests_available",
    "license",
    "local_path",
    "notes",
]

DISCOVERY_LOG_COLUMNS = [
    "discovery_id",
    "route",
    "platform",
    "query_or_seed",
    "searched_on",
    "result_count",
    "screened_count",
    "included_count",
    "screening_rule",
    "notes",
]

DISCOVERY_RESULTS_COLUMNS = [
    "discovery_id",
    "result_rank",
    "repository",
    "path",
    "url",
    "screening_decision",
    "source_id",
    "exclusion_reason",
    "notes",
]

ALLOWED_ARTIFACT_TYPES = {
    "ontology",
    "vocabulary",
    "shacl",
    "specification",
    "profile",
    "example_data",
    "test_data",
    "documentation",
}

ALLOWED_AUTHORITATIVE_STATUS = {
    "official",
    "official_generated",
    "community",
    "research",
    "unknown",
}

ALLOWED_GENERATION_METHODS = {
    "manual",
    "generated",
    "mixed",
    "unknown",
}

ALLOWED_SCREENING_DECISIONS = {
    "candidate",
    "included",
    "excluded",
}

ALLOWED_RESULT_SCREENING_DECISIONS = {
    "candidate",
    "included",
    "excluded",
    "duplicate",
}

URL_FIELDS = {
    "sources": ("homepage", "repository"),
    "artifacts": ("url",),
}

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DISCOVERY_COUNT_FIELDS = ("result_count", "screened_count", "included_count")


def is_blank(value: str | None) -> bool:
    return value is None or value.strip() == ""


def is_valid_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_valid_iso_date(value: str) -> bool:
    return bool(DATE_RE.fullmatch(value.strip()))


def is_non_negative_int(value: str) -> bool:
    text = value.strip()
    if not text.isdigit():
        return False
    return int(text) >= 0


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = [{key: (row.get(key) or "") for key in fieldnames} for row in reader]
    return fieldnames, rows


def check_required_columns(
    path: Path,
    fieldnames: list[str],
    required: list[str],
    errors: list[str],
) -> None:
    missing = [column for column in required if column not in fieldnames]
    if missing:
        errors.append(f"{path}: missing required columns: {', '.join(missing)}")


def validate_urls(
    path: Path,
    rows: list[dict[str, str]],
    fields: tuple[str, ...],
    id_field: str,
    errors: list[str],
) -> None:
    for index, row in enumerate(rows, start=2):
        row_id = row.get(id_field, "") or f"row {index}"
        for field in fields:
            value = row.get(field, "")
            if is_blank(value):
                continue
            if not is_valid_url(value):
                errors.append(
                    f"{path}:{index}: {row_id}: invalid URL in '{field}': {value!r}"
                )


def validate_enum(
    path: Path,
    rows: list[dict[str, str]],
    field: str,
    allowed: set[str],
    id_field: str,
    errors: list[str],
) -> None:
    for index, row in enumerate(rows, start=2):
        value = row.get(field, "")
        row_id = row.get(id_field, "") or f"row {index}"
        if is_blank(value):
            errors.append(f"{path}:{index}: {row_id}: missing required field '{field}'")
            continue
        if value not in allowed:
            allowed_text = ", ".join(sorted(allowed))
            errors.append(
                f"{path}:{index}: {row_id}: invalid '{field}' value {value!r}; "
                f"allowed: {allowed_text}"
            )


def check_unique_ids(
    path: Path,
    rows: list[dict[str, str]],
    id_field: str,
    errors: list[str],
) -> set[str]:
    seen: dict[str, int] = {}
    ids: set[str] = set()
    for index, row in enumerate(rows, start=2):
        value = row.get(id_field, "").strip()
        if is_blank(value):
            errors.append(f"{path}:{index}: missing required field '{id_field}'")
            continue
        if value in seen:
            errors.append(
                f"{path}:{index}: duplicate {id_field} {value!r} "
                f"(first seen at line {seen[value]})"
            )
        else:
            seen[value] = index
            ids.add(value)
    return ids


def validate_screening_decisions(
    path: Path,
    rows: list[dict[str, str]],
    errors: list[str],
) -> None:
    for index, row in enumerate(rows, start=2):
        source_id = row.get("source_id", "") or f"row {index}"
        decision = row.get("screening_decision", "").strip()
        reason = row.get("exclusion_reason", "").strip()

        if is_blank(decision):
            errors.append(
                f"{path}:{index}: {source_id}: missing required field 'screening_decision'"
            )
            continue

        if decision not in ALLOWED_SCREENING_DECISIONS:
            allowed_text = ", ".join(sorted(ALLOWED_SCREENING_DECISIONS))
            errors.append(
                f"{path}:{index}: {source_id}: invalid 'screening_decision' value "
                f"{decision!r}; allowed: {allowed_text}"
            )
            continue

        if decision == "excluded" and is_blank(reason):
            errors.append(
                f"{path}:{index}: {source_id}: excluded sources must have an "
                "exclusion_reason"
            )


def validate_discovery_log(
    path: Path,
    rows: list[dict[str, str]],
    errors: list[str],
) -> None:
    check_unique_ids(path, rows, "discovery_id", errors)

    for index, row in enumerate(rows, start=2):
        discovery_id = row.get("discovery_id", "") or f"row {index}"
        searched_on = row.get("searched_on", "")
        screening_rule = row.get("screening_rule", "")

        if is_blank(screening_rule):
            errors.append(
                f"{path}:{index}: {discovery_id}: missing required field "
                "'screening_rule'"
            )

        if not is_blank(searched_on) and not is_valid_iso_date(searched_on):
            errors.append(
                f"{path}:{index}: {discovery_id}: 'searched_on' must use YYYY-MM-DD "
                f"when present; got {searched_on!r}"
            )

        for field in DISCOVERY_COUNT_FIELDS:
            value = row.get(field, "")
            if is_blank(value):
                continue
            if not is_non_negative_int(value):
                errors.append(
                    f"{path}:{index}: {discovery_id}: '{field}' must be a "
                    f"non-negative integer when present; got {value!r}"
                )


def validate_discovery_results(
    path: Path,
    rows: list[dict[str, str]],
    source_ids: set[str],
    errors: list[str],
) -> None:
    seen_pairs: dict[tuple[str, str], int] = {}

    for index, row in enumerate(rows, start=2):
        discovery_id = (row.get("discovery_id") or "").strip()
        result_rank = (row.get("result_rank") or "").strip()
        decision = (row.get("screening_decision") or "").strip()
        source_id = (row.get("source_id") or "").strip()
        exclusion_reason = (row.get("exclusion_reason") or "").strip()
        row_label = discovery_id or f"row {index}"

        if is_blank(discovery_id):
            errors.append(
                f"{path}:{index}: missing required field 'discovery_id'"
            )

        if is_blank(result_rank):
            errors.append(
                f"{path}:{index}: {row_label}: missing required field 'result_rank'"
            )
        elif not is_non_negative_int(result_rank):
            errors.append(
                f"{path}:{index}: {row_label}: 'result_rank' must be a non-negative "
                f"integer; got {result_rank!r}"
            )
        else:
            pair = (discovery_id, result_rank)
            if pair in seen_pairs:
                errors.append(
                    f"{path}:{index}: {row_label}: duplicate "
                    f"(discovery_id, result_rank)=({discovery_id!r}, {result_rank!r}); "
                    f"first seen at line {seen_pairs[pair]}"
                )
            else:
                seen_pairs[pair] = index

        if is_blank(decision):
            errors.append(
                f"{path}:{index}: {row_label}: missing required field "
                "'screening_decision'"
            )
        elif decision not in ALLOWED_RESULT_SCREENING_DECISIONS:
            allowed_text = ", ".join(sorted(ALLOWED_RESULT_SCREENING_DECISIONS))
            errors.append(
                f"{path}:{index}: {row_label}: invalid 'screening_decision' value "
                f"{decision!r}; allowed: {allowed_text}"
            )

        if not is_blank(source_id) and source_id not in source_ids:
            errors.append(
                f"{path}:{index}: {row_label}: unknown source_id {source_id!r}"
            )

        if decision == "excluded" and is_blank(exclusion_reason):
            errors.append(
                f"{path}:{index}: {row_label}: excluded results must have an "
                "exclusion_reason"
            )


def validate_manifest() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    if not SOURCES_PATH.exists():
        errors.append(f"missing file: {SOURCES_PATH}")
    if not ARTIFACTS_PATH.exists():
        errors.append(f"missing file: {ARTIFACTS_PATH}")
    if not DISCOVERY_LOG_PATH.exists():
        errors.append(f"missing file: {DISCOVERY_LOG_PATH}")
    if not DISCOVERY_RESULTS_PATH.exists():
        errors.append(f"missing file: {DISCOVERY_RESULTS_PATH}")

    if errors:
        for message in errors:
            print(f"ERROR: {message}")
        print(f"\nValidation failed with {len(errors)} error(s).")
        return 1

    source_fields, source_rows = load_csv(SOURCES_PATH)
    artifact_fields, artifact_rows = load_csv(ARTIFACTS_PATH)
    discovery_fields, discovery_rows = load_csv(DISCOVERY_LOG_PATH)
    result_fields, result_rows = load_csv(DISCOVERY_RESULTS_PATH)

    check_required_columns(SOURCES_PATH, source_fields, SOURCE_COLUMNS, errors)
    check_required_columns(ARTIFACTS_PATH, artifact_fields, ARTIFACT_COLUMNS, errors)
    check_required_columns(
        DISCOVERY_LOG_PATH, discovery_fields, DISCOVERY_LOG_COLUMNS, errors
    )
    check_required_columns(
        DISCOVERY_RESULTS_PATH, result_fields, DISCOVERY_RESULTS_COLUMNS, errors
    )

    source_ids = check_unique_ids(SOURCES_PATH, source_rows, "source_id", errors)
    check_unique_ids(ARTIFACTS_PATH, artifact_rows, "artifact_id", errors)

    validate_urls(
        SOURCES_PATH,
        source_rows,
        URL_FIELDS["sources"],
        "source_id",
        errors,
    )
    validate_urls(
        ARTIFACTS_PATH,
        artifact_rows,
        URL_FIELDS["artifacts"],
        "artifact_id",
        errors,
    )

    validate_screening_decisions(SOURCES_PATH, source_rows, errors)
    validate_discovery_log(DISCOVERY_LOG_PATH, discovery_rows, errors)
    validate_discovery_results(
        DISCOVERY_RESULTS_PATH, result_rows, source_ids, errors
    )

    validate_enum(
        ARTIFACTS_PATH,
        artifact_rows,
        "artifact_type",
        ALLOWED_ARTIFACT_TYPES,
        "artifact_id",
        errors,
    )
    validate_enum(
        ARTIFACTS_PATH,
        artifact_rows,
        "authoritative_status",
        ALLOWED_AUTHORITATIVE_STATUS,
        "artifact_id",
        errors,
    )
    validate_enum(
        ARTIFACTS_PATH,
        artifact_rows,
        "generation_method",
        ALLOWED_GENERATION_METHODS,
        "artifact_id",
        errors,
    )

    for index, row in enumerate(artifact_rows, start=2):
        artifact_id = row.get("artifact_id", "") or f"row {index}"
        source_id = row.get("source_id", "").strip()

        if is_blank(source_id):
            errors.append(
                f"{ARTIFACTS_PATH}:{index}: {artifact_id}: missing required field 'source_id'"
            )
        elif source_id not in source_ids:
            errors.append(
                f"{ARTIFACTS_PATH}:{index}: {artifact_id}: "
                f"unknown source_id {source_id!r}"
            )

        version = row.get("version", "")
        commit_or_release = row.get("commit_or_release", "")
        if is_blank(version) and is_blank(commit_or_release):
            warnings.append(
                f"{ARTIFACTS_PATH}:{index}: {artifact_id}: "
                "missing version and commit_or_release"
            )
        elif is_blank(version):
            warnings.append(
                f"{ARTIFACTS_PATH}:{index}: {artifact_id}: missing version"
            )
        elif is_blank(commit_or_release):
            warnings.append(
                f"{ARTIFACTS_PATH}:{index}: {artifact_id}: missing commit_or_release"
            )

        intended_target = row.get("intended_target", "")
        if is_blank(intended_target):
            warnings.append(
                f"{ARTIFACTS_PATH}:{index}: {artifact_id}: "
                "no identifiable intended_target"
            )

    for message in warnings:
        print(f"WARNING: {message}")
    for message in errors:
        print(f"ERROR: {message}")

    if errors:
        print(
            f"\nValidation failed with {len(errors)} error(s) "
            f"and {len(warnings)} warning(s)."
        )
        return 1

    print(
        f"Validation passed with {len(warnings)} warning(s). "
        f"Checked {len(source_rows)} source(s), {len(artifact_rows)} artifact(s), "
        f"{len(discovery_rows)} discovery log row(s), "
        f"and {len(result_rows)} discovery result row(s)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(validate_manifest())
