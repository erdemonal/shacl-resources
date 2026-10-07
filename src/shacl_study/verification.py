"""Milestone 2: pin a revision and look for shape-defining SHACL in RDF."""

from __future__ import annotations

import hashlib
import json
import tarfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

from shacl_study.github_client import (
    ArchiveTooLarge,
    GitHubAuthError,
    GitHubClient,
    GitHubRequestError,
)
from shacl_study.rdf_evidence import GraphEvidence, classify_graph, parse_rdf
from shacl_study.shacl_vocab import ShaclVocabulary, default_vocabulary, prefilter_needles
from shacl_study.storage import write_csv

CORE_REQUESTS_PER_REPOSITORY = 2
LFS_MARKER = b"version https://git-lfs.github.com/spec/v1"
PARSER_FORMATS = {
    "extension:.ttl": "turtle",
    "extension:.shacl": "turtle",
    "extension:.trig": "trig",
    "extension:.n3": "n3",
    "extension:.nt": "nt",
    "extension:.nq": "nquads",
    "extension:.rdf": "xml",
    "extension:.owl": "xml",
    "extension:.jsonld": "json-ld",
    "extension:.json-ld": "json-ld",
    "sniff:rdfxml": "xml",
    "sniff:jsonld": "json-ld",
}
PILOT_STRATA = (
    ("targeted_code", 10),
    ("code_broad_only", 8),
    ("topic_only", 8),
    ("broad_repository_only", 8),
    ("fork", 8),
    ("archived", 8),
)
REPO_COLUMNS = [
    "repository_id",
    "repository_full_name",
    "commit_sha_examined",
    "verification_status",
    "verification_reason",
    "inspection_complete",
    "candidate_files_found",
    "files_examined",
    "rdf_files_parsed",
    "files_with_verified_shacl",
    "node_shape_count",
    "property_shape_count",
    "shacl_core_evidence_count",
    "shacl_sparql_evidence_count",
    "other_shacl_iri_count",
    "parse_failures",
    "skipped_too_large",
    "default_branch",
    "tree_sha",
    "inspection_timestamp",
    "verification_evidence",
    "noncanonical_shacl_namespace_detected",
    "noncanonical_namespace",
    "noncanonical_evidence",
    "pilot_stratum",
    "is_fork",
    "archived",
    "content_source",
    "prefilter_gate",
]
FILE_COLUMNS = [
    "repository_id",
    "repository_full_name",
    "commit_sha_examined",
    "path",
    "candidate_rule",
    "byte_size",
    "content_sha256",
    "fetch_status",
    "parse_status",
    "parser_format",
    "text_prefilter_hit",
    "node_shape_count",
    "property_shape_count",
    "shacl_core_evidence_count",
    "shacl_sparql_evidence_count",
    "other_shacl_iri_count",
    "verification_evidence",
    "noncanonical_namespace",
    "noncanonical_evidence",
    "parse_error",
]
FAILURE_COLUMNS = [
    "repository_id",
    "repository_full_name",
    "commit_sha_examined",
    "path",
    "failure_kind",
    "http_status",
    "detail",
]


class ClassifiedFailure(Exception):
    def __init__(self, kind: str, status: int, detail: str):
        super().__init__(detail)
        self.kind = kind
        self.status = status
        self.detail = detail


@dataclass
class FileResult:
    path: str
    candidate_rule: str = ""
    accepted: bool = False
    fetch_status: str = ""
    parse_status: str = ""
    parser_format: str = ""
    text_hit: bool = False
    evidence: GraphEvidence | None = None
    byte_size: int = 0
    content_sha256: str = ""
    parse_error: str = ""
    http_status: int | None = None
    failure_kind: str = ""
    failure_detail: str = ""
    payload: bytes | None = None


@dataclass
class Inspection:
    commit_sha: str = ""
    tree_sha: str = ""
    content_source: str = ""
    access_kind: str = ""
    access_reason: str = ""
    access_status: int | None = None
    access_detail: str = ""
    cap_hit: bool = False
    heuristic_paths: int = 0
    archive_too_large: bool = False
    tarball_failure: ClassifiedFailure | None = None
    files: list[FileResult] = field(default_factory=list)


def load_verification_config(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    required = (
        "max_file_bytes",
        "max_candidate_files",
        "max_archive_bytes",
        "strong_extensions",
        "sniff_extensions",
    )
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"verification config missing {', '.join(missing)}")
    data["strong_extensions"] = {str(item).lower() for item in data["strong_extensions"]}
    data["sniff_extensions"] = {str(key).lower(): value for key, value in data["sniff_extensions"].items()}
    data["max_file_bytes"] = int(data["max_file_bytes"])
    data["max_candidate_files"] = int(data["max_candidate_files"])
    data["max_archive_bytes"] = int(data["max_archive_bytes"])
    return data


def config_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def failure_class(status: int, message: str) -> str:
    text = message.lower()
    if status in {404, 410, 451, 409}:
        return "inaccessible"
    if status == 403 and "rate limit" not in text and "secondary rate" not in text:
        return "inaccessible"
    return "transient"


def evidence_families(discovered_by: str) -> set[str]:
    families: set[str] = set()
    for label in discovered_by.split("|"):
        if label.startswith("code:canonical_namespace"):
            families.add("canonical_namespace")
        elif label.startswith("code:shacl_class_name"):
            families.add("shacl_class_name")
        elif label.startswith("code:shacl_term"):
            families.add("shacl_term")
        elif label.startswith("code:shacl_full_iri"):
            families.add("shacl_full_iri")
        elif label.startswith("code:broad_text"):
            families.add("code_broad_text")
        elif label == "repository:repository_topic":
            families.add("repository_topic")
        elif label == "repository:broad_text":
            families.add("repository_broad_text")
    return families


def has_code_signal(discovered_by: str) -> bool:
    return any(part.startswith("code:") for part in discovered_by.split("|") if part)


def select_code_signal(rows: list[dict]) -> list[dict]:
    """Phase 1: repositories found by at least one code-search family."""
    selected = []
    for row in rows:
        if not has_code_signal(row.get("discovered_by", "")):
            continue
        picked = dict(row)
        picked["pilot_stratum"] = "code_signal"
        selected.append(picked)
    return selected


def select_pilot(rows: list[dict], size: int = 50) -> list[dict]:
    quotas = _quotas(size)
    selected: list[dict] = []
    used: set[str] = set()
    predicates = {
        "targeted_code": lambda row: _targeted(row) and not _flag(row, "is_fork") and not _flag(row, "archived"),
        "code_broad_only": lambda row: evidence_families(row["discovered_by"]) == {"code_broad_text"}
        and not _flag(row, "is_fork"),
        "topic_only": lambda row: _topic_only(row) and not _flag(row, "is_fork") and not _flag(row, "archived"),
        "broad_repository_only": lambda row: evidence_families(row["discovered_by"]) == {"repository_broad_text"}
        and not _flag(row, "is_fork")
        and not _flag(row, "archived"),
        "fork": lambda row: _flag(row, "is_fork"),
        "archived": lambda row: _flag(row, "archived"),
    }
    for (name, _), quota in zip(PILOT_STRATA, quotas, strict=True):
        pool = [row for row in rows if row["repository_id"] not in used and predicates[name](row)]
        for row in _spaced(pool, quota):
            used.add(row["repository_id"])
            picked = dict(row)
            picked["pilot_stratum"] = name
            selected.append(picked)
    return selected


def inspect_repository(
    row: dict,
    *,
    source,
    vocab: ShaclVocabulary,
    config: dict,
    clock,
) -> tuple[dict, list[dict], list[dict]]:
    timestamp = clock().strftime("%Y-%m-%dT%H:%M:%SZ")
    prefilter_gate = not has_code_signal(row.get("discovered_by", ""))
    inspection = _collect(row, source=source, config=config)
    repository_row, failures = _decide(
        row,
        inspection,
        prefilter_gate=prefilter_gate,
        timestamp=timestamp,
    )
    file_rows = [
        _file_row(row, inspection.commit_sha, item)
        for item in inspection.files
        if item.accepted
    ]
    return repository_row, file_rows, failures


def tarball_entries(archive: Path, config: dict) -> list[dict]:
    entries: list[dict] = []
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar:
            if not member.isfile():
                continue
            path = _archive_path(member.name)
            if not path or not raw_extension_rule(path, config):
                continue
            if member.size > int(config["max_file_bytes"]):
                entries.append({"path": path, "size": member.size, "content": None, "too_large": True})
                continue
            extracted = tar.extractfile(member)
            content = extracted.read() if extracted is not None else b""
            entries.append({"path": path, "size": len(content), "content": content, "too_large": False})
    return entries


def raw_extension_rule(path: str, config: dict) -> str:
    extension = _extension(path)
    if extension in config["strong_extensions"]:
        return f"extension:{extension}"
    if extension in config["sniff_extensions"]:
        return f"provisional:{extension}"
    return ""


class GitHubContent:
    def __init__(self, client: GitHubClient, config: dict):
        self.client = client
        self.config = config

    def resolve_commit(self, full_name: str, branch: str) -> dict:
        return _translate(lambda: self.client.resolve_commit(full_name, branch))

    def get_tree(self, full_name: str, tree_sha: str) -> dict:
        return _translate(lambda: self.client.get_git_tree(full_name, tree_sha))

    def get_file(self, full_name: str, commit_sha: str, path: str) -> bytes:
        return _translate(lambda: self.client.get_raw_file(full_name, commit_sha, path))

    def list_tarball(self, full_name: str, commit_sha: str) -> list[dict]:
        try:
            archive = self.client.download_tarball(
                full_name,
                commit_sha,
                max_bytes=int(self.config["max_archive_bytes"]),
            )
        except ArchiveTooLarge as exc:
            raise exc
        except GitHubRequestError as exc:
            raise ClassifiedFailure(failure_class(exc.status, exc.message), exc.status, exc.message) from exc
        return tarball_entries(archive, self.config)


def run_verification(
    *,
    rows: list[dict],
    source,
    vocab: ShaclVocabulary | None,
    config: dict,
    config_digest: str,
    data_dir: Path,
    fresh: bool,
    clock,
    logger,
    phase: str = "",
    git_commit: str | None = None,
    git_dirty: bool | None = None,
) -> dict:
    vocab = vocab or default_vocabulary()
    state_path = data_dir / "candidates" / "verification_state.json"
    state = _load_state(state_path, config_digest, vocab.sha256, fresh)
    if phase == "1":
        _write_phase_manifest(
            data_dir / "results" / "phase1_manifest.json",
            {
                "milestone": 2,
                "phase": 1,
                "scope": "Repositories with at least one code-search signal.",
                "started_at": clock().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "git_commit": git_commit,
                "git_dirty": git_dirty,
                "repository_count": len(rows),
                "canonical_namespace": "http://www.w3.org/ns/shacl#",
                "noncanonical_status": "noncanonical_shacl_namespace",
                "verification_config_sha256": config_digest,
                "vocabulary_sha256": vocab.sha256,
            },
        )
    repository_rows: list[dict] = []
    file_rows: list[dict] = []
    failure_rows: list[dict] = []
    for index, row in enumerate(rows, start=1):
        key = str(row["repository_id"])
        cached = state["repositories"].get(key)
        if cached and cached.get("verification_status") != "transient_failure":
            repository_rows.append(cached["repository"])
            file_rows.extend(cached["files"])
            failure_rows.extend(cached["failures"])
            continue
        logger.info(
            "verify %s/%s %s stratum=%s",
            index,
            len(rows),
            row["repository_full_name"],
            row.get("pilot_stratum", ""),
        )
        repository, files, failures = inspect_repository(
            row,
            source=source,
            vocab=vocab,
            config=config,
            clock=clock,
        )
        state["repositories"][key] = {"repository": repository, "files": files, "failures": failures}
        if repository["verification_status"] != "transient_failure":
            _write_state(state_path, state)
        repository_rows.append(repository)
        file_rows.extend(files)
        failure_rows.extend(failures)
        logger.info(
            "status %s %s complete=%s",
            row["repository_full_name"],
            repository["verification_status"],
            repository["inspection_complete"],
        )
    results = data_dir / "results"
    write_csv(results / "repository_verification.csv", REPO_COLUMNS, repository_rows)
    write_csv(results / "shacl_file_verification.csv", FILE_COLUMNS, file_rows)
    write_csv(results / "milestone2_failures.csv", FAILURE_COLUMNS, failure_rows)
    summary = _summary(
        rows=rows,
        repository_rows=repository_rows,
        vocab=vocab,
        config=config,
        config_digest=config_digest,
        source=source,
        clock=clock,
        phase=phase,
        git_commit=git_commit,
        git_dirty=git_dirty,
    )
    (results / "milestone2_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if phase == "1":
        finished = dict(summary)
        finished["finished_at"] = clock().strftime("%Y-%m-%dT%H:%M:%SZ")
        _write_phase_manifest(results / "phase1_manifest.json", finished)
    _write_state(state_path, state)
    return summary


def _collect(row: dict, *, source, config: dict) -> Inspection:
    inspection = Inspection()
    branch = row.get("default_branch") or ""
    full_name = row["repository_full_name"]
    if not branch:
        inspection.access_kind = "inaccessible"
        inspection.access_reason = "missing_default_branch"
        inspection.access_detail = "Candidate row has no default branch."
        return inspection
    try:
        pin = source.resolve_commit(full_name, branch)
    except ClassifiedFailure as exc:
        inspection.access_kind = exc.kind
        inspection.access_reason = f"commit_{exc.kind}"
        inspection.access_status = exc.status
        inspection.access_detail = exc.detail
        return inspection
    inspection.commit_sha = pin["commit_sha"]
    inspection.tree_sha = pin["tree_sha"]
    try:
        tree = source.get_tree(full_name, pin["tree_sha"])
    except ClassifiedFailure as exc:
        inspection.access_kind = exc.kind
        inspection.access_reason = f"tree_{exc.kind}"
        inspection.access_status = exc.status
        inspection.access_detail = exc.detail
        return inspection
    if tree.get("truncated"):
        inspection.content_source = "codeload_tarball"
        try:
            blobs = source.list_tarball(full_name, pin["commit_sha"])
        except ArchiveTooLarge as exc:
            inspection.archive_too_large = True
            inspection.access_detail = str(exc)
            return inspection
        except ClassifiedFailure as exc:
            inspection.tarball_failure = exc
            return inspection
        _examine_known_blobs(inspection, row, blobs, config=config, vocab_needles=_needles(config))
        return inspection
    inspection.content_source = "git_tree"
    entries = []
    for item in tree.get("tree") or []:
        if item.get("type") != "blob":
            continue
        path = str(item.get("path") or "")
        if _unsafe_path(path) or not raw_extension_rule(path, config):
            continue
        entries.append({"path": path, "size": item.get("size"), "content": None, "too_large": False})
    _examine_tree_entries(
        inspection,
        row,
        entries,
        source=source,
        config=config,
    )
    return inspection


def _examine_tree_entries(inspection: Inspection, row: dict, entries: list[dict], *, source, config: dict) -> None:
    inspection.heuristic_paths = len(entries)
    chosen, inspection.cap_hit = _cap_entries(entries, int(config["max_candidate_files"]))
    needles = _needles(config)
    for entry in chosen:
        path = entry["path"]
        result = FileResult(path=path, candidate_rule=raw_extension_rule(path, config))
        size = entry.get("size")
        if isinstance(size, int) and size > int(config["max_file_bytes"]):
            result.accepted = True
            result.byte_size = size
            result.fetch_status = "skipped_too_large"
            result.parse_status = "skipped_too_large"
            result.failure_kind = "skipped_too_large"
            inspection.files.append(result)
            continue
        try:
            payload = source.get_file(row["repository_full_name"], inspection.commit_sha, path)
        except ClassifiedFailure as exc:
            result.accepted = not result.candidate_rule.startswith("provisional:")
            result.fetch_status = "fetch_error"
            result.failure_kind = exc.kind
            result.http_status = exc.status
            result.failure_detail = exc.detail
            result.parse_status = "fetch_error"
            inspection.files.append(result)
            continue
        _consume_payload(result, payload, config=config, needles=needles)
        inspection.files.append(result)


def _examine_known_blobs(inspection: Inspection, row: dict, blobs: list[dict], *, config: dict, vocab_needles) -> None:
    del row
    inspection.heuristic_paths = len(blobs)
    chosen, inspection.cap_hit = _cap_entries(blobs, int(config["max_candidate_files"]))
    for entry in chosen:
        result = FileResult(path=entry["path"], candidate_rule=raw_extension_rule(entry["path"], config))
        if entry.get("too_large"):
            result.accepted = True
            result.byte_size = int(entry.get("size") or 0)
            result.fetch_status = "skipped_too_large"
            result.parse_status = "skipped_too_large"
            result.failure_kind = "skipped_too_large"
            inspection.files.append(result)
            continue
        _consume_payload(result, entry.get("content") or b"", config=config, needles=vocab_needles)
        inspection.files.append(result)


def _decide(row: dict, inspection: Inspection, *, prefilter_gate: bool, timestamp: str) -> tuple[dict, list[dict]]:
    _parse_when_required(inspection, prefilter_gate=prefilter_gate)
    accepted = [item for item in inspection.files if item.accepted]
    status, reason, complete = _status(inspection, accepted, prefilter_gate=prefilter_gate)
    evidence_names = sorted({name for item in accepted if item.evidence for name in item.evidence.evidence})
    repository = {
        "repository_id": row["repository_id"],
        "repository_full_name": row["repository_full_name"],
        "commit_sha_examined": inspection.commit_sha,
        "verification_status": status,
        "verification_reason": reason,
        "inspection_complete": complete,
        "candidate_files_found": len(accepted),
        "files_examined": sum(1 for item in accepted if item.fetch_status == "fetched"),
        "rdf_files_parsed": sum(1 for item in accepted if item.parse_status == "parsed"),
        "files_with_verified_shacl": sum(1 for item in accepted if item.evidence and item.evidence.verifies),
        "node_shape_count": _shape_count(accepted, "node_shape_subjects"),
        "property_shape_count": _shape_count(accepted, "property_shape_subjects"),
        "shacl_core_evidence_count": sum(item.evidence.core_triples for item in accepted if item.evidence),
        "shacl_sparql_evidence_count": sum(item.evidence.sparql_triples for item in accepted if item.evidence),
        "other_shacl_iri_count": sum(item.evidence.other_triples for item in accepted if item.evidence),
        "parse_failures": sum(1 for item in accepted if item.parse_status == "parse_error"),
        "skipped_too_large": sum(1 for item in accepted if item.parse_status == "skipped_too_large"),
        "default_branch": row.get("default_branch", ""),
        "tree_sha": inspection.tree_sha,
        "inspection_timestamp": timestamp,
        "verification_evidence": "|".join(evidence_names),
        "noncanonical_shacl_namespace_detected": _noncanonical_detected(accepted),
        "noncanonical_namespace": "|".join(_noncanonical_namespaces(accepted)),
        "noncanonical_evidence": "|".join(_noncanonical_terms(accepted)),
        "pilot_stratum": row.get("pilot_stratum", ""),
        "is_fork": row.get("is_fork", ""),
        "archived": row.get("archived", ""),
        "content_source": inspection.content_source,
        "prefilter_gate": prefilter_gate,
    }
    failures: list[dict] = []
    if inspection.access_kind:
        failures.append(
            _failure(
                row,
                inspection.commit_sha,
                "",
                inspection.access_kind if inspection.access_kind != "transient" else "transient_failure",
                inspection.access_status,
                inspection.access_detail,
            )
        )
    if inspection.archive_too_large:
        failures.append(
            _failure(row, inspection.commit_sha, "", "incomplete_inspection", None, inspection.access_detail)
        )
    if inspection.tarball_failure is not None:
        kind = "transient_failure" if inspection.tarball_failure.kind == "transient" else "inaccessible"
        failures.append(
            _failure(
                row,
                inspection.commit_sha,
                "",
                kind,
                inspection.tarball_failure.status,
                inspection.tarball_failure.detail,
            )
        )
    if inspection.cap_hit:
        failures.append(
            _failure(
                row,
                inspection.commit_sha,
                "",
                "candidate_file_cap",
                None,
                f"heuristic_paths={inspection.heuristic_paths}",
            )
        )
    for item in accepted:
        if item.failure_kind:
            failures.append(
                _failure(
                    row,
                    inspection.commit_sha,
                    item.path,
                    item.failure_kind,
                    item.http_status,
                    item.failure_detail or item.parse_error,
                )
            )
    return repository, failures


def _parse_when_required(inspection: Inspection, *, prefilter_gate: bool) -> None:
    accepted = [item for item in inspection.files if item.accepted and item.parse_status == "not_parsed"]
    if not accepted:
        return
    if prefilter_gate and not any(item.text_hit for item in accepted):
        return
    vocab = _vocab_for_parse()
    for result in accepted:
        if result.parse_status != "not_parsed":
            continue
        parser_format = PARSER_FORMATS.get(result.candidate_rule, "")
        result.parser_format = parser_format
        payload = result.payload
        if payload is None:
            result.parse_status = "fetch_error"
            result.failure_kind = "fetch_error"
            result.failure_detail = "Fetched bytes were not retained for parsing."
            continue
        if not parser_format:
            result.parse_status = "parser_unavailable"
            result.failure_kind = "parser_unavailable"
            result.parse_error = f"No parser mapped for {result.candidate_rule}"
            continue
        try:
            graph = parse_rdf(payload, parser_format)
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            if parser_format == "json-ld" and "plugin" in message.lower():
                result.parse_status = "parser_unavailable"
                result.failure_kind = "parser_unavailable"
                result.parse_error = message[:500]
            else:
                result.parse_status = "parse_error"
                result.failure_kind = "parse_error"
                result.parse_error = message[:500]
            continue
        result.parse_status = "parsed"
        result.evidence = classify_graph(graph, vocab)


def _vocab_for_parse() -> ShaclVocabulary:
    return default_vocabulary()


def _status(inspection: Inspection, accepted: list[FileResult], *, prefilter_gate: bool) -> tuple[str, str, bool]:
    if inspection.access_kind == "inaccessible" and not inspection.commit_sha:
        return "inaccessible", inspection.access_reason or "inaccessible", False
    if inspection.access_kind == "transient" and not accepted:
        return "transient_failure", inspection.access_reason or "transient_failure", False
    if inspection.access_kind == "inaccessible" and not accepted:
        return "inaccessible", inspection.access_reason or "inaccessible", False
    if inspection.tarball_failure is not None and not accepted:
        if inspection.tarball_failure.kind == "transient":
            return "transient_failure", "tarball_fetch_failed", False
        return "inaccessible", "tarball_unavailable", False
    verified = [item for item in accepted if item.evidence and item.evidence.verifies]
    operational = _operational_reason(inspection, accepted)
    if verified:
        cores = sum(item.evidence.core_triples for item in verified if item.evidence)
        sparqls = sum(item.evidence.sparql_triples for item in verified if item.evidence)
        if cores and sparqls:
            reason = "core_and_sparql_shape_evidence"
        elif sparqls:
            reason = "sparql_shape_evidence"
        else:
            reason = "core_shape_evidence"
        return "verified_shacl", reason, operational == "" and _parses_complete(accepted)
    if _noncanonical_terms(accepted):
        return (
            "noncanonical_shacl_namespace",
            "https_shacl_namespace",
            operational == "" and _parses_complete(accepted),
        )
    if inspection.archive_too_large:
        return "incomplete_inspection", "archive_over_size_cap", False
    if operational:
        return "incomplete_inspection", operational, False
    if any(item.parse_status == "parse_error" for item in accepted):
        return "parse_failure_only", "parse_error", False
    if not accepted:
        return "not_verified", "no_candidate_rdf_files", False
    if prefilter_gate and not any(item.text_hit for item in accepted):
        return "not_verified", "prefilter_no_shacl_signal", False
    if any(item.parse_status != "parsed" for item in accepted):
        return "incomplete_inspection", "unparsed_candidate", False
    if any(item.evidence and item.evidence.other_triples for item in accepted):
        return "not_verified", "other_shacl_iri_only", True
    return "no_shacl_found", "parsed_candidate_files_without_shacl_terms", True


def _operational_reason(inspection: Inspection, accepted: list[FileResult]) -> str:
    if inspection.cap_hit:
        return "candidate_file_cap"
    if any(item.parse_status == "skipped_too_large" for item in accepted):
        return "skipped_too_large"
    if any(item.parse_status == "lfs_pointer" for item in accepted):
        return "lfs_pointer"
    if any(item.parse_status == "parser_unavailable" for item in accepted):
        return "parser_unavailable"
    if any(item.fetch_status == "fetch_error" for item in accepted):
        return "fetch_error"
    return ""


def _parses_complete(accepted: list[FileResult]) -> bool:
    return all(item.parse_status == "parsed" for item in accepted)


def _noncanonical_detected(accepted: list[FileResult]) -> bool:
    return any(item.evidence and item.evidence.noncanonical_detected for item in accepted)


def _noncanonical_namespaces(accepted: list[FileResult]) -> list[str]:
    found: set[str] = set()
    for item in accepted:
        if item.evidence:
            found.update(item.evidence.noncanonical_namespaces)
    return sorted(found)


def _noncanonical_terms(accepted: list[FileResult]) -> list[str]:
    found: set[str] = set()
    for item in accepted:
        if item.evidence:
            found.update(item.evidence.noncanonical_shape_terms)
    return sorted(found)


def _shape_count(accepted: list[FileResult], attribute: str) -> int:
    uris: set[str] = set()
    blanks = 0
    for item in accepted:
        if item.evidence is None:
            continue
        for subject in getattr(item.evidence, attribute):
            if subject.startswith("bnode:"):
                blanks += 1
            else:
                uris.add(subject)
    return len(uris) + blanks


def _cap_entries(entries: list[dict], limit: int) -> tuple[list[dict], bool]:
    ordered = sorted(entries, key=lambda item: item["path"])
    if len(ordered) <= limit:
        return ordered, False
    return ordered[:limit], True


def _extension(path: str) -> str:
    name = path.rsplit("/", 1)[-1].lower()
    if name.endswith(".json-ld"):
        return ".json-ld"
    dot = name.rfind(".")
    if dot < 0:
        return ""
    return name[dot:]


def _sniff(extension: str, payload: bytes) -> str:
    head = payload[:65536].decode("utf-8", errors="ignore")
    if extension == ".xml" and ("rdf:RDF" in head or "http://www.w3.org/1999/02/22-rdf-syntax-ns#" in head):
        return "sniff:rdfxml"
    if extension == ".json" and '"@context"' in head:
        return "sniff:jsonld"
    return ""


def _text_hit(payload: bytes, needles: tuple[str, ...]) -> bool:
    haystack = payload.decode("utf-8", errors="ignore")
    return any(needle in haystack for needle in needles)


def _needles(config: dict) -> tuple[str, ...]:
    del config
    return prefilter_needles(default_vocabulary())


def _unsafe_path(path: str) -> bool:
    return path.startswith("/") or ".." in path.split("/")


def _archive_path(name: str) -> str:
    parts = [part for part in name.split("/") if part and part != "."]
    if len(parts) <= 1:
        return ""
    relative = parts[1:]
    if ".." in relative:
        return ""
    return "/".join(relative)


def _file_row(row: dict, commit_sha: str, item: FileResult) -> dict:
    evidence = item.evidence
    return {
        "repository_id": row["repository_id"],
        "repository_full_name": row["repository_full_name"],
        "commit_sha_examined": commit_sha,
        "path": item.path,
        "candidate_rule": item.candidate_rule,
        "byte_size": item.byte_size,
        "content_sha256": item.content_sha256,
        "fetch_status": item.fetch_status,
        "parse_status": item.parse_status,
        "parser_format": item.parser_format,
        "text_prefilter_hit": item.text_hit,
        "node_shape_count": len(evidence.node_shape_subjects) if evidence else 0,
        "property_shape_count": len(evidence.property_shape_subjects) if evidence else 0,
        "shacl_core_evidence_count": evidence.core_triples if evidence else 0,
        "shacl_sparql_evidence_count": evidence.sparql_triples if evidence else 0,
        "other_shacl_iri_count": evidence.other_triples if evidence else 0,
        "verification_evidence": "|".join(sorted(evidence.evidence)) if evidence else "",
        "noncanonical_namespace": "|".join(sorted(evidence.noncanonical_namespaces)) if evidence else "",
        "noncanonical_evidence": "|".join(sorted(evidence.noncanonical_shape_terms)) if evidence else "",
        "parse_error": item.parse_error,
    }


def _failure(row: dict, commit_sha: str, path: str, kind: str, status: int | None, detail: str) -> dict:
    return {
        "repository_id": row["repository_id"],
        "repository_full_name": row["repository_full_name"],
        "commit_sha_examined": commit_sha,
        "path": path,
        "failure_kind": kind,
        "http_status": "" if status is None else status,
        "detail": detail[:500],
    }


def _quotas(size: int) -> list[int]:
    weights = [quota for _, quota in PILOT_STRATA]
    total = sum(weights)
    raw = [size * weight / total for weight in weights]
    base = [int(value) for value in raw]
    remainder = size - sum(base)
    order = sorted(range(len(base)), key=lambda index: (raw[index] - base[index], -index), reverse=True)
    for index in order[:remainder]:
        base[index] += 1
    return base


def _spaced(rows: list[dict], count: int) -> list[dict]:
    ordered = sorted(rows, key=lambda row: int(row["repository_id"]))
    if count <= 0 or not ordered:
        return []
    if len(ordered) <= count:
        return ordered
    indexes: list[int] = []
    seen: set[int] = set()
    for step in range(count):
        index = round(step * (len(ordered) - 1) / (count - 1))
        if index not in seen:
            seen.add(index)
            indexes.append(index)
    return [ordered[index] for index in indexes]


def _targeted(row: dict) -> bool:
    families = evidence_families(row["discovered_by"])
    return bool(families & {"canonical_namespace", "shacl_class_name", "shacl_term", "shacl_full_iri"})


def _topic_only(row: dict) -> bool:
    families = evidence_families(row["discovered_by"])
    return "repository_topic" in families and not has_code_signal(row["discovered_by"])


def _flag(row: dict, column: str) -> bool:
    return str(row.get(column, "")).lower() == "true"


def _translate(call):
    try:
        return call()
    except GitHubAuthError:
        raise
    except GitHubRequestError as exc:
        raise ClassifiedFailure(failure_class(exc.status, exc.message), exc.status, exc.message) from exc


def _load_state(path: Path, config_digest: str, vocab_sha: str, fresh: bool) -> dict:
    if fresh and path.exists():
        path.unlink()
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("config_sha256") != config_digest or state.get("vocab_sha256") != vocab_sha:
            raise SystemExit("Verification state does not match this config or vocabulary. Re-run with --fresh.")
        return state
    return {"config_sha256": config_digest, "vocab_sha256": vocab_sha, "repositories": {}}


def _write_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state), encoding="utf-8")


def _write_phase_manifest(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _summary(
    *,
    rows: list[dict],
    repository_rows: list[dict],
    vocab: ShaclVocabulary,
    config: dict,
    config_digest: str,
    source,
    clock,
    phase: str = "",
    git_commit: str | None = None,
    git_dirty: bool | None = None,
) -> dict:
    counts: dict[str, int] = {}
    for row in repository_rows:
        counts[row["verification_status"]] = counts.get(row["verification_status"], 0) + 1
    network = getattr(getattr(source, "client", None), "network_requests", {})
    return {
        "milestone": 2,
        "phase": phase or None,
        "mode": "phase1" if phase == "1" else ("pilot" if any(row.get("pilot_stratum") for row in rows) else "selection"),
        "git_commit": git_commit,
        "git_dirty": git_dirty,
        "collected_at": clock().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repository_count": len(repository_rows),
        "status_counts": counts,
        "inspection_complete_true": sum(1 for row in repository_rows if str(row["inspection_complete"]) == "true" or row["inspection_complete"] is True),
        "limits": {
            "max_file_bytes": config["max_file_bytes"],
            "max_candidate_files": config["max_candidate_files"],
            "max_archive_bytes": config["max_archive_bytes"],
        },
        "verification_config_sha256": config_digest,
        "vocabulary": vocab.as_report(),
        "rule": {
            "verified_shacl": (
                "At least one parsed RDF graph contains rdf:type sh:NodeShape, "
                "rdf:type sh:PropertyShape, a derived SHACL Core target or constraint-parameter "
                "predicate, sh:path as declared for property shapes, or a derived SHACL-SPARQL "
                "evidence predicate (sh:sparql, sh:select, sh:ask, sh:construct, sh:update). "
                "A SHACL namespace IRI alone does not verify. "
                "https://www.w3.org/ns/shacl# is not rewritten to the canonical http namespace. "
                "Shape structures that use only the https IRI are noncanonical_shacl_namespace."
            ),
            "prefilter": (
                "Repositories with no code-search signal are parsed only when a candidate file's "
                "bytes contain the SHACL namespace IRI or a derived shape predicate. "
                "A prefilter miss is not_verified/prefilter_no_shacl_signal with inspection_complete false."
            ),
            "no_shacl_found": (
                "Every accepted candidate file was parsed, none contained a SHACL-namespace IRI, "
                "and no operational limit was hit."
            ),
        },
        "api": {
            "core_requests_per_repository": CORE_REQUESTS_PER_REPOSITORY,
            "network_requests_observed": network,
            "full_corpus_core_requests_at_15075": 15075 * CORE_REQUESTS_PER_REPOSITORY,
            "full_corpus_core_hours_at_5000_per_hour": round(15075 * CORE_REQUESTS_PER_REPOSITORY / 5000, 2),
        },
        "pilot_repositories": [
            {
                "repository_id": row["repository_id"],
                "repository_full_name": row["repository_full_name"],
                "pilot_stratum": row.get("pilot_stratum", ""),
                "verification_status": row["verification_status"],
                "verification_reason": row["verification_reason"],
                "inspection_complete": row["inspection_complete"],
                "commit_sha_examined": row["commit_sha_examined"],
            }
            for row in repository_rows
        ],
    }


# Retain fetched bytes on the file result so the parser can run after the prefilter decision.
def _consume_payload(result: FileResult, payload: bytes, *, config: dict, needles: tuple[str, ...]) -> None:
    result.payload = payload
    result.byte_size = len(payload)
    result.content_sha256 = hashlib.sha256(payload).hexdigest()
    result.fetch_status = "fetched"
    if len(payload) > int(config["max_file_bytes"]):
        result.accepted = True
        result.fetch_status = "skipped_too_large"
        result.parse_status = "skipped_too_large"
        result.failure_kind = "skipped_too_large"
        result.payload = None
        return
    if payload.startswith(LFS_MARKER):
        result.accepted = True
        result.parse_status = "lfs_pointer"
        result.failure_kind = "lfs_pointer"
        return
    rule = result.candidate_rule
    if rule.startswith("provisional:"):
        sniffed = _sniff(rule.removeprefix("provisional:"), payload)
        if not sniffed:
            result.accepted = False
            result.parse_status = "sniff_rejected"
            return
        result.candidate_rule = sniffed
    result.accepted = True
    result.text_hit = _text_hit(payload, needles)
    result.parse_status = "not_parsed"
