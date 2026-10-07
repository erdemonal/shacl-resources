import csv
import io
import tarfile
from datetime import datetime, timezone
from pathlib import Path

from shacl_study.discovery_hits import load_code_search_paths
from shacl_study.github_client import ArchiveTooLarge, raw_content_url
from shacl_study.shacl_vocab import default_vocabulary
from shacl_study.verification import (
    FAILURE_COLUMNS,
    FILE_COLUMNS,
    REPO_COLUMNS,
    ClassifiedFailure,
    inspect_repository,
    load_verification_config,
    run_verification,
    select_pilot,
    tarball_entries,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_verification_config(ROOT / "config" / "verification.yaml")
CLOCK = lambda: datetime(2026, 10, 7, tzinfo=timezone.utc)
REQUIRED_REPO_COLUMNS = [
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
]


NODE = b"""\
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix ex: <http://example.org/> .
ex:PersonShape a sh:NodeShape ;
  sh:targetClass ex:Person ;
  sh:property [
    a sh:PropertyShape ;
    sh:path ex:name ;
    sh:minCount 1
  ] .
"""
SPARQL = b"""\
@prefix sh: <http://www.w3.org/ns/shacl#> .
[] sh:sparql [ sh:select "SELECT $this WHERE { }" ] .
"""
IMPORTS = b"""\
@prefix owl: <http://www.w3.org/2002/07/owl#> .
<http://example.org/vocab> owl:imports <http://www.w3.org/ns/shacl#> .
"""
NAME_ONLY = b"""\
@prefix sh: <http://www.w3.org/ns/shacl#> .
[] sh:name "label" .
"""
PREFIX_ONLY = b"@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
PLAIN = b"@prefix ex: <http://example.org/> .\nex:a ex:b ex:c .\n"
BROKEN = b"@prefix sh: <http://www.w3.org/ns/shacl#> .\nthis is not turtle .\n"
SELECT_ONLY = b"""\
@prefix sh: <http://www.w3.org/ns/shacl#> .
[] sh:select \"SELECT * WHERE { ?s ?p ?o }\" .
"""
TYPED_SPARQL = b"""\
@prefix sh: <http://www.w3.org/ns/shacl#> .
[] a sh:SPARQLConstraint ; sh:select \"SELECT $this WHERE { }\" .
"""
QUERY_CATALOG = b"""\
@prefix sh: <http://www.w3.org/ns/shacl#> .
<http://example.org/NXQ> a sh:SPARQLExecutable, sh:SPARQLSelectExecutable ;
  sh:select \"SELECT * WHERE { ?s ?p ?o }\" .
"""


class MemorySource:
    def __init__(self, files, *, truncated=False, commit_error=None, tree_error=None, tarball=None, sizes=None, file_errors=None, extra=None):
        self.files = files
        self.truncated = truncated
        self.commit_error = commit_error
        self.tree_error = tree_error
        self.tarball = tarball
        self.sizes = sizes or {}
        self.file_errors = file_errors or {}
        self.extra = extra or {}
        self.calls = []
        self.commit_sha = "a" * 40
        self.tree_sha = "b" * 40

    def resolve_commit(self, full_name, branch):
        self.calls.append(("commit", branch))
        if self.commit_error:
            raise self.commit_error
        return {"commit_sha": self.commit_sha, "tree_sha": self.tree_sha}

    def get_tree(self, full_name, tree_sha):
        self.calls.append(("tree", tree_sha))
        if self.tree_error:
            raise self.tree_error
        if self.truncated:
            return {"truncated": True, "sha": tree_sha, "tree": []}
        tree = []
        for path, payload in self.files.items():
            tree.append(
                {
                    "path": path,
                    "type": "blob",
                    "size": self.sizes.get(path, len(payload)),
                    "sha": "c" * 40,
                }
            )
        return {"truncated": False, "sha": tree_sha, "tree": tree}

    def get_file(self, full_name, commit_sha, path):
        self.calls.append(("file", commit_sha, path))
        if path in self.file_errors:
            raise self.file_errors[path]
        if path in self.extra:
            return self.extra[path]
        return self.files[path]

    def peek_file(self, full_name, commit_sha, path, max_bytes=65536):
        self.calls.append(("peek", commit_sha, path))
        if path in self.file_errors:
            raise self.file_errors[path]
        payload = self.extra.get(path, self.files[path])
        if len(payload) <= max_bytes:
            return payload, True
        return payload[:max_bytes], False

    def list_tarball(self, full_name, commit_sha):
        self.calls.append(("tarball", commit_sha))
        if isinstance(self.tarball, Exception):
            raise self.tarball
        return self.tarball or []


def _row(**overrides):
    row = {
        "repository_id": "1",
        "repository_full_name": "acme/shapes",
        "default_branch": "main",
        "discovered_by": "code:shacl_class_name:primary",
        "is_fork": "false",
        "archived": "false",
        "pilot_stratum": "",
    }
    row.update(overrides)
    return row


def _inspect(files, **kwargs):
    row = kwargs.pop("row", _row())
    hit_paths = kwargs.pop("hit_paths", None)
    config_updates = kwargs.pop("config_updates", None)
    source = MemorySource(files, **kwargs)
    config = dict(CONFIG)
    if config_updates:
        config.update(config_updates)
    repository, file_rows, failures = inspect_repository(
        row,
        source=source,
        vocab=default_vocabulary(),
        config=config,
        clock=CLOCK,
        hit_paths=hit_paths,
    )
    return repository, file_rows, failures, source


def test_vocabulary_keeps_sparql_out_of_core():
    vocab = default_vocabulary()
    core = {iri.rsplit("#", 1)[-1] for iri in vocab.core_predicates}
    sparql = {iri.rsplit("#", 1)[-1] for iri in vocab.sparql_evidence_predicates}
    assert {"minCount", "targetClass", "property", "path", "qualifiedValueShape"} <= core
    assert "sparql" not in core
    assert "select" not in core
    assert "ask" not in core
    assert "name" not in core
    assert "js" not in core
    assert "expression" not in core
    assert sparql == {"sparql", "ask", "select", "construct", "update"}
    types = {iri.rsplit("#", 1)[-1] for iri in vocab.sparql_constraint_types}
    assert "SPARQLConstraint" in types
    assert "SPARQLSelectExecutable" not in types
    assert "SPARQLExecutable" not in types
    assert {iri.rsplit("#", 1)[-1] for iri in vocab.excluded_components} == {
        "SPARQLConstraintComponent",
        "JSConstraintComponent",
        "ExpressionConstraintComponent",
    }


def test_node_shape_is_core_evidence_and_pins_commit():
    repository, files, _, source = _inspect({"shapes/person.ttl": NODE})
    assert repository["verification_status"] == "verified_shacl"
    assert repository["verification_reason"] == "core_shape_evidence"
    assert repository["inspection_complete"] is True
    assert repository["commit_sha_examined"] == "a" * 40
    assert repository["tree_sha"] == "b" * 40
    assert repository["node_shape_count"] == 1
    assert repository["property_shape_count"] == 1
    assert int(repository["shacl_core_evidence_count"]) > 0
    assert repository["shacl_sparql_evidence_count"] == 0
    assert "rdf:type sh:NodeShape" in repository["verification_evidence"]
    assert files[0]["candidate_rule"] == "extension:.ttl"
    assert ("file", "a" * 40, "shapes/person.ttl") in source.calls
    assert all(call[1] != "main" for call in source.calls if call[0] == "file")


def test_sparql_evidence_is_separate_from_core():
    repository, _, _, _ = _inspect({"shape.ttl": SPARQL})
    assert repository["verification_status"] == "verified_shacl"
    assert repository["verification_reason"] == "sparql_shape_evidence"
    assert repository["shacl_core_evidence_count"] == 0
    assert int(repository["shacl_sparql_evidence_count"]) >= 2
    assert "sh:sparql" in repository["verification_evidence"]
    assert "sh:select" in repository["verification_evidence"]


def test_standalone_sparql_select_does_not_verify():
    repository, _, _, _ = _inspect({"query.ttl": SELECT_ONLY})
    assert repository["verification_status"] != "verified_shacl"
    assert repository["shacl_sparql_evidence_count"] == 0
    typed, _, _, _ = _inspect({"constraint.ttl": TYPED_SPARQL})
    assert typed["verification_status"] == "verified_shacl"
    assert typed["verification_reason"] == "sparql_shape_evidence"
    assert "sh:select" in typed["verification_evidence"]
    catalog, _, _, _ = _inspect({"catalog.ttl": QUERY_CATALOG})
    assert catalog["verification_status"] != "verified_shacl"
    assert catalog["shacl_sparql_evidence_count"] == 0


def test_tier1_verification_does_not_download_generic_xml():
    repository, _, _, source = _inspect({"data/feed.xml": b"<not-rdf/>", "shapes/person.ttl": NODE})
    assert repository["verification_status"] == "verified_shacl"
    assert repository["verification_stopped_early"] is True
    assert not any(call[0] in {"file", "peek"} and str(call[-1]).endswith(".xml") for call in source.calls)


def test_unresolved_tier1_peeks_xml_instead_of_downloading_it():
    repository, _, _, source = _inspect({"notes.ttl": PLAIN, "data/feed.xml": b"<not-rdf/>" * 20000})
    assert repository["verification_status"] == "no_shacl_found"
    assert ("peek", "a" * 40, "data/feed.xml") in source.calls
    assert not any(call[0] == "file" and call[-1] == "data/feed.xml" for call in source.calls)


def test_large_tier1_set_uses_one_tarball():
    files = {f"f{index}.ttl": PLAIN for index in range(5)}
    files["a.ttl"] = NODE
    tarball = [
        {"path": path, "size": len(payload), "content": payload, "too_large": False} for path, payload in files.items()
    ]
    repository, _, _, source = _inspect(
        files,
        tarball=tarball,
        config_updates={"tarball_candidate_threshold": 3},
    )
    assert repository["verification_status"] == "verified_shacl"
    assert repository["content_source"] == "codeload_tarball"
    assert ("tarball", "a" * 40) in source.calls
    assert not any(call[0] == "file" for call in source.calls)


def test_oversized_tarball_falls_back_to_selective_files():
    repository, _, failures, source = _inspect(
        {"a.ttl": NODE, "b.ttl": PLAIN, "c.ttl": PLAIN},
        tarball=ArchiveTooLarge(999),
        config_updates={"tarball_candidate_threshold": 2},
    )
    assert repository["verification_status"] == "verified_shacl"
    assert repository["content_source"] == "git_tree"
    assert any(item["failure_kind"] == "tarball_over_size_cap" for item in failures)
    assert any(call[0] == "file" for call in source.calls)


def test_namespace_import_and_name_do_not_verify():
    imports, _, _, _ = _inspect({"vocab.ttl": IMPORTS})
    assert imports["verification_status"] == "not_verified"
    assert imports["verification_reason"] == "other_shacl_iri_only"
    assert imports["inspection_complete"] is True
    name_only, _, _, _ = _inspect({"vocab.ttl": NAME_ONLY})
    assert name_only["verification_status"] == "not_verified"
    assert name_only["verification_reason"] == "other_shacl_iri_only"


def test_prefix_declaration_alone_is_not_shape_evidence():
    repository, _, _, _ = _inspect({"shape.ttl": PREFIX_ONLY})
    assert repository["verification_status"] == "no_shacl_found"
    assert repository["inspection_complete"] is True


def test_prefilter_miss_is_not_absence():
    repository, files, _, _ = _inspect(
        {"notes.ttl": PLAIN},
        row=_row(discovered_by="repository:broad_text"),
    )
    assert repository["verification_status"] == "not_verified"
    assert repository["verification_reason"] == "prefilter_no_shacl_signal"
    assert repository["inspection_complete"] is False
    assert files[0]["parse_status"] == "not_parsed"
    assert "no_shacl" not in repository["verification_status"]


def test_same_plain_file_is_parsed_for_code_signal_repository():
    repository, files, _, _ = _inspect({"notes.ttl": PLAIN})
    assert repository["verification_status"] == "no_shacl_found"
    assert repository["inspection_complete"] is True
    assert files[0]["parse_status"] == "parsed"


def test_no_candidate_files_are_not_called_free_of_shacl():
    repository, _, _, _ = _inspect({"README.md": b"This project uses SHACL.\n"})
    assert repository["verification_status"] == "not_verified"
    assert repository["verification_reason"] == "no_candidate_rdf_files"
    assert repository["inspection_complete"] is False


def test_parse_error_does_not_stop_the_other_file_and_is_not_repaired():
    repository, files, failures, _ = _inspect({"bad.ttl": BROKEN, "ok.ttl": NODE})
    assert repository["verification_status"] == "verified_shacl"
    assert repository["inspection_complete"] is False
    assert repository["parse_failures"] == 1
    assert {item["path"]: item["parse_status"] for item in files} == {
        "bad.ttl": "parse_error",
        "ok.ttl": "parsed",
    }
    assert any(item["failure_kind"] == "parse_error" and item["path"] == "bad.ttl" for item in failures)


def test_parse_failure_only_when_nothing_else_resolves():
    repository, _, _, _ = _inspect({"bad.ttl": BROKEN})
    assert repository["verification_status"] == "parse_failure_only"
    assert repository["inspection_complete"] is False


def test_oversized_file_is_incomplete_not_ambiguous():
    config = dict(CONFIG)
    config["max_file_bytes"] = 10
    source = MemorySource({"huge.ttl": NODE}, sizes={"huge.ttl": 500})
    repository, _, failures = inspect_repository(
        _row(),
        source=source,
        vocab=default_vocabulary(),
        config=config,
        clock=CLOCK,
    )
    assert repository["verification_status"] == "incomplete_inspection"
    assert repository["verification_reason"] == "skipped_too_large"
    assert repository["inspection_complete"] is False
    assert repository["skipped_too_large"] == 1
    assert "ambiguous" not in repository["verification_status"]
    assert not any(call[0] == "file" for call in source.calls)
    assert any(item["failure_kind"] == "skipped_too_large" for item in failures)


def test_missing_repository_is_inaccessible_and_timeout_is_transient():
    missing, _, _, _ = _inspect(
        {},
        commit_error=ClassifiedFailure("inaccessible", 404, "HTTP 404: Not Found"),
    )
    assert missing["verification_status"] == "inaccessible"
    assert missing["commit_sha_examined"] == ""
    timed_out, _, _, _ = _inspect({}, commit_error=ClassifiedFailure("transient", 0, "timed out"))
    assert timed_out["verification_status"] == "transient_failure"
    assert timed_out["inspection_complete"] is False


def test_truncated_tree_uses_tarball_fallback_instead_of_the_branch_name():
    payload = NODE
    source_args = {
        "truncated": True,
        "tarball": [{"path": "shapes/person.ttl", "size": len(payload), "content": payload, "too_large": False}],
    }
    repository, files, _, source = _inspect({}, **source_args)
    assert repository["verification_status"] == "verified_shacl"
    assert repository["content_source"] == "codeload_tarball"
    assert repository["commit_sha_examined"] == "a" * 40
    assert ("tarball", "a" * 40) in source.calls
    assert not any(call[0] == "file" for call in source.calls)
    assert files[0]["candidate_rule"] == "extension:.ttl"


def test_truncated_tree_without_tarball_is_not_a_negative_finding():
    repository, _, _, _ = _inspect(
        {},
        truncated=True,
        tarball=ClassifiedFailure("transient", 503, "HTTP 503"),
    )
    assert repository["verification_status"] == "transient_failure"
    assert repository["verification_reason"] == "tarball_fetch_failed"


def test_fork_and_archived_rows_are_verified():
    repository, _, _, _ = _inspect(
        {"shape.ttl": NODE},
        row=_row(is_fork="true", archived="true", discovered_by="repository:broad_text|code:shacl_term:fork_only"),
    )
    assert repository["verification_status"] == "verified_shacl"
    assert repository["is_fork"] == "true"
    assert repository["archived"] == "true"


def test_raw_url_uses_the_commit_sha():
    url = raw_content_url("acme/shapes", "abc123", "shapes/my file.ttl")
    assert "/abc123/" in url
    assert "main" not in url
    assert "my%20file.ttl" in url


def test_tarball_entries_keep_rdf_and_drop_readme(tmp_path):
    archive = tmp_path / "repo.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        _add(tar, "repo-sha/shapes/a.ttl", NODE)
        _add(tar, "repo-sha/README.md", b"SHACL\n")
    entries = tarball_entries(archive, CONFIG)
    assert [item["path"] for item in entries] == ["shapes/a.ttl"]


def test_pilot_selection_is_stratified_and_disjoint():
    rows = []
    identifier = 1

    def add(count, discovered_by, fork="false", archived="false"):
        nonlocal identifier
        for _ in range(count):
            rows.append(
                {
                    "repository_id": str(identifier),
                    "repository_full_name": f"org/repo-{identifier}",
                    "discovered_by": discovered_by,
                    "is_fork": fork,
                    "archived": archived,
                }
            )
            identifier += 1

    add(30, "code:shacl_class_name:primary")
    add(30, "code:broad_text:primary")
    add(30, "repository:repository_topic|repository:broad_text")
    add(30, "repository:broad_text")
    add(30, "repository:broad_text", fork="true")
    add(30, "repository:broad_text", archived="true")
    selected = select_pilot(rows, 50)
    assert len(selected) == 50
    assert len({row["repository_id"] for row in selected}) == 50
    counts = {}
    for row in selected:
        counts[row["pilot_stratum"]] = counts.get(row["pilot_stratum"], 0) + 1
    assert counts == {
        "targeted_code": 10,
        "code_broad_only": 8,
        "topic_only": 8,
        "broad_repository_only": 8,
        "fork": 8,
        "archived": 8,
    }
    assert all(row["is_fork"] == "true" for row in selected if row["pilot_stratum"] == "fork")
    assert all(row["archived"] == "true" for row in selected if row["pilot_stratum"] == "archived")


def test_run_writes_the_verification_tables(tmp_path):
    row = _row()
    summary = run_verification(
        rows=[row],
        source=MemorySource({"shape.ttl": NODE}),
        vocab=default_vocabulary(),
        config=dict(CONFIG),
        config_digest="abc",
        data_dir=tmp_path,
        fresh=True,
        clock=CLOCK,
        logger=_logger(),
    )
    repo_header = next(csv.reader((tmp_path / "results" / "repository_verification.csv").open()))
    file_header = next(csv.reader((tmp_path / "results" / "shacl_file_verification.csv").open()))
    failure_header = next(csv.reader((tmp_path / "results" / "milestone2_failures.csv").open()))
    for column in REQUIRED_REPO_COLUMNS:
        assert column in repo_header
    assert repo_header == REPO_COLUMNS
    assert file_header == FILE_COLUMNS
    assert failure_header == FAILURE_COLUMNS
    assert summary["status_counts"]["verified_shacl"] == 1
    assert summary["limits"]["max_file_bytes"] == CONFIG["max_file_bytes"]
    assert "sparql" not in summary["vocabulary"]["core_constraint_parameters"]
    assert summary["api"]["core_requests_per_repository"] == 2


def _add(tar, name, payload):
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    tar.addfile(info, io.BytesIO(payload))


def _logger():
    import logging

    logger = logging.getLogger("verification-test")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    return logger


HTTPS_SHAPE = b"""\
@prefix sh1: <https://www.w3.org/ns/shacl#> .
@prefix ex: <http://example.org/> .
ex:Shape_Asset a sh1:NodeShape ;
  sh1:targetClass ex:Asset ;
  sh1:property [ sh1:path ex:name ; sh1:minCount 1 ] .
"""
HTTPS_IMPORT = b"""\
@prefix owl: <http://www.w3.org/2002/07/owl#> .
<http://example.org/vocab> owl:imports <https://www.w3.org/ns/shacl#> .
"""


def test_https_shape_is_recorded_apart_from_canonical_verification():
    repository, files, _, _ = _inspect({"energy_shacl.ttl": HTTPS_SHAPE})
    assert repository["verification_status"] == "noncanonical_shacl_namespace"
    assert repository["verification_reason"] == "https_shacl_namespace"
    assert repository["noncanonical_shacl_namespace_detected"] is True
    assert repository["noncanonical_namespace"] == "https://www.w3.org/ns/shacl#"
    assert repository["shacl_core_evidence_count"] == 0
    assert repository["node_shape_count"] == 0
    for term in ("NodeShape", "targetClass", "path", "minCount", "property"):
        assert term in repository["noncanonical_evidence"].split("|")
    assert files[0]["path"] == "energy_shacl.ttl"
    assert files[0]["noncanonical_namespace"] == "https://www.w3.org/ns/shacl#"


def test_https_does_not_replace_canonical_verification():
    repository, _, _, _ = _inspect({"a-https.ttl": HTTPS_SHAPE, "b-canonical.ttl": NODE})
    assert repository["verification_status"] == "verified_shacl"
    assert repository["noncanonical_shacl_namespace_detected"] is True
    assert int(repository["node_shape_count"]) == 1


def test_https_import_without_a_shape_is_not_verified():
    repository, _, _, _ = _inspect({"vocab.ttl": HTTPS_IMPORT})
    assert repository["verification_status"] == "no_shacl_found"
    assert repository["noncanonical_shacl_namespace_detected"] is True
    assert repository["noncanonical_evidence"] == ""


def test_discovery_hit_verifies_without_walking_the_tree():
    repository, files, _, source = _inspect(
        {"shapes/person.ttl": NODE, "other/noise.ttl": PLAIN},
        hit_paths=["shapes/person.ttl", "README.md"],
    )
    assert repository["verification_status"] == "verified_shacl"
    assert repository["verification_reason"] == "core_shape_evidence"
    assert repository["verification_pass"] == "discovery_hit"
    assert repository["evidence_path"] == "shapes/person.ttl"
    assert repository["inspection_complete"] is False
    assert repository["content_source"] == "discovery_hit"
    assert repository["commit_sha_examined"] == "a" * 40
    assert files[0]["path"] == "shapes/person.ttl"
    assert ("tree", "b" * 40) not in source.calls
    assert ("file", "a" * 40, "README.md") not in source.calls


def test_unresolved_discovery_hit_falls_back_and_is_not_a_negative_finding():
    repository, _, _, source = _inspect(
        {"notes.md": b"# SHACL\n", "shapes/person.ttl": NODE},
        hit_paths=["notes.md"],
    )
    assert repository["verification_status"] == "verified_shacl"
    assert repository["verification_pass"] == "tree_inspection"
    assert repository["evidence_path"] == "shapes/person.ttl"
    assert ("tree", "b" * 40) in source.calls
    assert repository["discovery_hit_files"] == 1


def test_broken_discovery_hit_does_not_hide_a_clean_tree():
    repository, _, _, _ = _inspect(
        {"plain.ttl": PLAIN},
        hit_paths=["orphan.ttl"],
        extra={"orphan.ttl": BROKEN},
    )
    assert repository["verification_status"] == "no_shacl_found"
    assert repository["verification_reason"] == "parsed_candidate_files_without_shacl_terms"
    assert repository["verification_pass"] == "tree_inspection"


def test_missing_discovery_hit_falls_back_to_the_tree():
    repository, _, _, source = _inspect(
        {"shapes/person.ttl": NODE},
        hit_paths=["gone.ttl"],
        file_errors={"gone.ttl": ClassifiedFailure("inaccessible", 404, "missing")},
    )
    assert repository["verification_status"] == "verified_shacl"
    assert repository["verification_pass"] == "tree_inspection"
    assert repository["evidence_path"] == "shapes/person.ttl"
    assert ("file", "a" * 40, "gone.ttl") in source.calls
    assert ("tree", "b" * 40) in source.calls


def test_https_discovery_hit_is_not_canonical_and_falls_back():
    repository, _, _, source = _inspect(
        {"energy_shacl.ttl": HTTPS_SHAPE},
        hit_paths=["energy_shacl.ttl"],
    )
    assert repository["verification_status"] == "noncanonical_shacl_namespace"
    assert repository["verification_pass"] == "tree_inspection"
    assert repository["noncanonical_shacl_namespace_detected"] is True
    assert ("tree", "b" * 40) in source.calls


def test_code_search_cache_keeps_the_matched_path(tmp_path):
    payload = {
        "total_count": 1,
        "incomplete_results": False,
        "items": [
            {
                "path": "examples/shape.ttl",
                "repository": {"id": 42, "full_name": "acme/shapes"},
            }
        ],
    }
    (tmp_path / "page.json").write_text(__import__("json").dumps(payload), encoding="utf-8")
    (tmp_path / "repo-search.json").write_text(
        __import__("json").dumps({"items": [{"id": 7, "full_name": "acme/other"}]}),
        encoding="utf-8",
    )
    assert load_code_search_paths(tmp_path) == {"42": ["examples/shape.ttl"]}


def test_failure_class_separates_not_found_from_rate_limit():
    from shacl_study.verification import failure_class

    assert failure_class(404, "HTTP 404: Not Found") == "inaccessible"
    assert failure_class(403, "HTTP 403: rate limit exceeded") == "transient"
    assert failure_class(403, "HTTP 403: Resource not accessible") == "inaccessible"
    assert failure_class(0, "timed out") == "transient"
