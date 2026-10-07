import csv
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from shacl_study.cli import main
from shacl_study.discovery import (
    _with_created_range,
    load_config,
    plan_queries,
    run_discovery,
    split_created_range,
)
from shacl_study.models import SearchPage
from shacl_study.storage import CANDIDATE_COLUMNS, QUERY_COLUMNS

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "discovery_queries.yaml"


class Clock:
    def __init__(self) -> None:
        self.moment = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        self.moment += timedelta(seconds=1)
        return self.moment


class FakeClient:
    def __init__(self, search_fn, repos: dict[str, dict]) -> None:
        self.search_fn = search_fn
        self.repos = repos
        self.search_calls: list[tuple] = []
        self.repo_calls: list[str] = []

    def search(self, endpoint: str, query: str, *, page: int, per_page: int) -> SearchPage:
        self.search_calls.append((endpoint, query, page, per_page))
        return self.search_fn(endpoint, query, page, per_page)

    def get_repository(self, full_name: str) -> dict:
        self.repo_calls.append(full_name)
        return self.repos[full_name]


def _repo(full_name: str, repo_id: int, **overrides) -> dict:
    payload = {
        "id": repo_id,
        "full_name": full_name,
        "html_url": f"https://github.com/{full_name}",
        "private": False,
        "visibility": "public",
        "fork": False,
        "archived": False,
        "stargazers_count": 3,
        "default_branch": "main",
        "license": {"spdx_id": "MIT"},
        "created_at": "2020-01-01T00:00:00Z",
        "updated_at": "2020-02-01T00:00:00Z",
        "pushed_at": "2020-03-01T00:00:00Z",
    }
    payload.update(overrides)
    return payload


def _page(total: int, repos: list[dict], *, incomplete: bool = False) -> SearchPage:
    return SearchPage(total_count=total, incomplete_results=incomplete, items=repos)


def _tiny_config() -> dict:
    return {
        "code_search": {
            "content_qualifier": "in:file",
            "fork_streams": [
                {"id": "primary", "qualifier": ""},
                {"id": "fork_only", "qualifier": "fork:only"},
            ],
            "extensions": ["ttl"],
            "queries": [
                {
                    "id": "class_node_shape",
                    "family": "shacl_class_name",
                    "term": '"sh:NodeShape"',
                    "partition_by_extension": True,
                },
                {
                    "id": "broad_shacl",
                    "family": "broad_text",
                    "term": "SHACL",
                    "partition_by_extension": False,
                },
            ],
        },
        "repository_search": {
            "public_qualifier": "is:public",
            "fork_qualifier": "fork:true",
            "date_partition_start": "2007-01-01",
            "queries": [
                {
                    "id": "topic_shacl",
                    "family": "repository_topic",
                    "term": "topic:shacl",
                    "date_partition": True,
                }
            ],
        },
    }


def _run(tmp_path: Path, client: FakeClient, **kwargs):
    arguments = {
        "config": _tiny_config(),
        "config_sha256": "test-config",
        "client": client,
        "data_dir": tmp_path,
        "fresh": True,
        "per_page": 100,
        "max_pages": None,
        "query_ids": None,
        "window_end": date(2020, 1, 10),
        "clock": Clock(),
    }
    arguments.update(kwargs)
    return run_discovery(**arguments)


def test_real_config_expands_separate_endpoint_queries():
    planned = plan_queries(load_config(CONFIG))
    assert len(planned) == 212
    code = [item for item in planned if item.endpoint == "code"]
    repository = [item for item in planned if item.endpoint == "repository"]
    assert len(code) == 210
    assert len(repository) == 2
    assert not any("fork:true" in item.query_text for item in code)

    namespace = next(item for item in code if item.query_id == "code__canonical_namespace__primary__ext_ttl")
    assert namespace.query_text == '"http://www.w3.org/ns/shacl#" in:file extension:ttl'
    assert namespace.partition == "stream:primary;extension:ttl"
    assert namespace.fork_stream == "primary"
    assert "is:public" not in namespace.query_text

    namespace_forks = next(item for item in code if item.query_id == "code__canonical_namespace__fork_only__ext_ttl")
    assert namespace_forks.query_text == '"http://www.w3.org/ns/shacl#" in:file fork:only extension:ttl'
    assert namespace_forks.partition == "stream:fork_only;fork:only;extension:ttl"
    assert namespace_forks.fork_stream == "fork_only"

    broad_code = next(item for item in code if item.query_id == "code__broad_shacl__primary")
    assert broad_code.query_text == "SHACL in:file"
    assert broad_code.partition == "stream:primary"
    assert "extension:" not in broad_code.query_text
    broad_forks = next(item for item in code if item.query_id == "code__broad_shacl__fork_only")
    assert broad_forks.query_text == "SHACL in:file fork:only"

    extensions = {item.partition.split("extension:")[1] for item in code if "extension:" in item.partition}
    assert extensions == {"ttl", "trig", "nt", "rdf", "xml", "owl", "jsonld", "nq"}

    topic = next(item for item in repository if item.query_id == "repository__topic_shacl")
    assert topic.query_text == "topic:shacl is:public fork:true"
    broad_repo = next(item for item in repository if item.query_id == "repository__broad_shacl")
    assert broad_repo.query_text == "SHACL in:name,description,readme,topics is:public fork:true"
    assert broad_repo.query_family == "broad_text"
    assert broad_code.query_family == "broad_text"
    assert broad_repo.endpoint != broad_code.endpoint

    quoted = next(item for item in code if item.query_id == "code__class_node_shape__primary__ext_ttl")
    assert quoted.query_text.startswith('"sh:NodeShape"')


def test_created_ranges_cover_every_day_once():
    start, end = date(2020, 1, 1), date(2020, 1, 10)

    def leaves(left: date, right: date) -> list[date]:
        halves = split_created_range(left, right)
        if halves is None:
            return [left]
        return leaves(*halves[0]) + leaves(*halves[1])

    assert leaves(start, end) == [start + timedelta(days=offset) for offset in range(10)]
    assert split_created_range(start, start) is None


def test_nested_date_partition_keeps_one_created_qualifier():
    topic = next(item for item in plan_queries(_tiny_config()) if item.endpoint == "repository")
    child = _with_created_range(topic, date(2007, 1, 1), date(2010, 1, 1))
    grandchild = _with_created_range(child, date(2007, 1, 1), date(2008, 6, 1))
    assert grandchild.query_text == "topic:shacl is:public fork:true created:2007-01-01..2008-06-01"
    assert grandchild.partition == "fork:true;created:2007-01-01..2008-06-01"


def test_repository_ceiling_is_date_partitioned_and_parent_hits_are_not_kept(tmp_path: Path):
    kept = _repo("org/kept", 2)
    skipped = _repo("org/skipped", 9)

    def search(endpoint, query, page, per_page):
        assert endpoint == "repository"
        assert page == 1
        if "created:" not in query:
            return _page(1000, [skipped])
        return _page(1, [kept])

    client = FakeClient(search, {"org/kept": kept})
    state = _run(tmp_path, client, query_ids=["repository__topic_shacl"])

    assert "org/skipped" not in {item.repository_full_name for item in state.candidates.values()}
    assert "org/kept" in {item.repository_full_name for item in state.candidates.values()}
    parent = state.executions["repository__topic_shacl"]
    assert parent.api_status == "split"
    assert parent.potentially_truncated is True
    assert "result_ceiling" in parent.truncation_reason
    assert all("created:" not in call[1] or call[1].count("created:") == 1 for call in client.search_calls)
    assert sum(item.api_status == "ok" for item in state.executions.values()) == 2


def test_code_search_ceiling_is_marked_and_not_date_partitioned(tmp_path: Path):
    found = _repo("org/shapes", 4)

    def search(endpoint, query, page, per_page):
        assert "created:" not in query
        assert endpoint == "code"
        if page == 1:
            return _page(1000, [{"repository": found}])
        return _page(1000, [])

    client = FakeClient(search, {"org/shapes": found})
    state = _run(tmp_path, client, query_ids=["code__broad_shacl__primary"])
    recorded = state.executions["code__broad_shacl__primary"]
    assert recorded.api_status == "truncated"
    assert recorded.potentially_truncated is True
    assert "result_ceiling" in recorded.truncation_reason
    assert recorded.pages_retrieved == 10
    assert len(state.candidates) == 1


def test_same_repository_keeps_both_query_provenances(tmp_path: Path):
    shared = _repo("org/shared", 7)

    def search(endpoint, query, page, per_page):
        return _page(1, [{"repository": shared}])

    client = FakeClient(search, {"org/shared": shared})
    state = _run(
        tmp_path,
        client,
        query_ids=["code__class_node_shape__primary__ext_ttl", "code__broad_shacl__primary"],
    )
    candidate = state.candidates["7"]
    assert candidate.discovery_queries == [
        "code__class_node_shape__primary__ext_ttl",
        "code__broad_shacl__primary",
    ]
    assert candidate.discovered_by == [
        "code:shacl_class_name:primary",
        "code:broad_text:primary",
    ]
    assert len(state.candidates) == 1


def test_primary_and_fork_only_hits_merge_by_repository_id(tmp_path: Path):
    shared = _repo("org/shared", 7, fork=True)

    def search(endpoint, query, page, per_page):
        return _page(1, [{"repository": shared}])

    client = FakeClient(search, {"org/shared": shared})
    state = _run(
        tmp_path,
        client,
        query_ids=[
            "code__class_node_shape__primary__ext_ttl",
            "code__class_node_shape__fork_only__ext_ttl",
        ],
    )
    assert len(state.candidates) == 1
    candidate = state.candidates["7"]
    assert candidate.discovery_queries == [
        "code__class_node_shape__primary__ext_ttl",
        "code__class_node_shape__fork_only__ext_ttl",
    ]
    assert candidate.discovered_by == [
        "code:shacl_class_name:primary",
        "code:shacl_class_name:fork_only",
    ]


def test_fork_parent_is_taken_from_repository_payload(tmp_path: Path):
    fork = _repo("org/fork", 8, fork=True)
    hydrated = _repo(
        "org/fork",
        8,
        fork=True,
        parent={"id": 99, "full_name": "org/upstream"},
    )

    def search(endpoint, query, page, per_page):
        return _page(1, [fork])

    client = FakeClient(search, {"org/fork": hydrated})
    state = _run(tmp_path, client, query_ids=["repository__topic_shacl"])
    candidate = state.candidates["8"]
    assert candidate.is_fork is True
    assert candidate.parent_repository_id == 99
    assert candidate.parent_repository_full_name == "org/upstream"


def test_hydration_removes_repository_that_is_not_public(tmp_path: Path):
    visible = _repo("org/hidden", 21)
    hidden = _repo("org/hidden", 21, private=True, visibility="private")

    def search(endpoint, query, page, per_page):
        return _page(1, [{"repository": visible}])

    client = FakeClient(search, {"org/hidden": hidden})
    state = _run(tmp_path, client, query_ids=["code__broad_shacl__primary"])
    assert state.candidates == {}
    assert state.nonpublic["21"].discovery_queries == ["code__broad_shacl__primary"]


def test_private_repository_is_removed_from_candidates(tmp_path: Path):
    private = _repo("org/private", 11, private=True, visibility="private")

    def search(endpoint, query, page, per_page):
        return _page(1, [{"repository": private}])

    client = FakeClient(search, {})
    state = _run(tmp_path, client, query_ids=["code__broad_shacl__primary"])
    assert state.candidates == {}
    assert state.nonpublic["11"].reason == "not_public"


def test_incomplete_results_are_marked_without_date_split(tmp_path: Path):
    found = _repo("org/partial", 12)

    def search(endpoint, query, page, per_page):
        assert "created:" not in query
        return _page(4, [found], incomplete=True)

    client = FakeClient(search, {"org/partial": found})
    state = _run(tmp_path, client, query_ids=["repository__topic_shacl"])
    recorded = state.executions["repository__topic_shacl"]
    assert recorded.api_status == "truncated"
    assert recorded.truncation_reason == "incomplete_results"
    assert len(client.search_calls) == 1


def test_local_page_limit_does_not_date_partition(tmp_path: Path):
    found = _repo("org/limited", 13)

    def search(endpoint, query, page, per_page):
        assert "created:" not in query
        return _page(1000, [found])

    client = FakeClient(search, {"org/limited": found})
    state = _run(tmp_path, client, query_ids=["repository__topic_shacl"], max_pages=1)
    recorded = state.executions["repository__topic_shacl"]
    assert recorded.api_status == "truncated"
    assert "local_page_limit" in recorded.truncation_reason
    assert "result_ceiling" in recorded.truncation_reason
    assert recorded.pages_retrieved == 1
    assert "org/limited" in {item.repository_full_name for item in state.candidates.values()}


def test_csv_schemas_are_discovery_only(tmp_path: Path):
    found = _repo("org/exported", 15)

    def search(endpoint, query, page, per_page):
        return _page(1, [found])

    client = FakeClient(search, {"org/exported": found})
    _run(tmp_path, client, query_ids=["repository__topic_shacl"])

    with (tmp_path / "results" / "candidate_repositories.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    with (tmp_path / "results" / "discovery_queries.csv").open(encoding="utf-8") as handle:
        query_rows = list(csv.DictReader(handle))

    assert list(rows[0]) == CANDIDATE_COLUMNS
    assert list(query_rows[0]) == QUERY_COLUMNS
    forbidden = {"verification_status", "inclusion_status", "number_of_node_shapes"}
    assert forbidden.isdisjoint(rows[0])
    assert rows[0]["repository_id"] == "15"
    assert rows[0]["is_fork"] == "false"
    assert rows[0]["stars"] == "3"
    assert rows[0]["license"] == "MIT"
    assert rows[0]["parent_repository_id"] == ""


def test_resume_skips_completed_query(tmp_path: Path):
    found = _repo("org/once", 16)

    def search(endpoint, query, page, per_page):
        return _page(1, [found])

    client = FakeClient(search, {"org/once": found})
    _run(tmp_path, client, query_ids=["repository__topic_shacl"])
    assert len(client.search_calls) == 1

    def fail_search(endpoint, query, page, per_page):
        raise AssertionError("completed query was executed again")

    second = FakeClient(fail_search, {"org/once": found})
    run_discovery(
        config=_tiny_config(),
        config_sha256="test-config",
        client=second,
        data_dir=tmp_path,
        fresh=False,
        per_page=100,
        max_pages=None,
        query_ids=["repository__topic_shacl"],
        window_end=date(2020, 1, 10),
        clock=Clock(),
    )
    assert second.search_calls == []
    assert second.repo_calls == []


def test_dry_run_prints_plan_without_token(capsys):
    exit_code = None
    try:
        main(["discover", "--dry-run", "--config", str(CONFIG)])
    except SystemExit as exc:
        exit_code = exc.code
    output = capsys.readouterr().out
    assert exit_code in (None, 0)
    assert "code__canonical_namespace__primary__ext_ttl" in output
    assert "code__canonical_namespace__fork_only__ext_ttl" in output
    assert "repository__topic_shacl" in output
    assert "# planned=212 code=210 repository=2" in output


def test_other_commands_are_not_implemented():
    for command in ("inspect", "stats", "audit", "run-all"):
        with pytest.raises(SystemExit, match="not implemented"):
            main([command])


def test_verify_refuses_an_unscoped_run():
    with pytest.raises(SystemExit, match="--pilot"):
        main(["verify"])
