# SHACL GitHub discovery

Milestone 1 discovers public GitHub repositories that may contain SHACL. It does not verify shapes, does not decide which repositories belong in an analytical subset, and does not compute constraint statistics.

Lieber et al. 2020, “Statistics about Data Shape Use in RDF Data”, reported preliminary SHACL Core constraint counts for a manually selected corpus. They searched GitHub for “SHACL”, kept repositories whose shapes looked valid and not like simple examples, and also included a small number of well-known shapes such as Schema.org SHACL. The poster reports 13 projects and 1,978 NodeShapes. The archive supplied with this repository does not reproduce those two figures under a direct count of explicit `sh:NodeShape` triples. That difference is unresolved and is written down in [notes/lieber-reproduction-notes.md](notes/lieber-reproduction-notes.md).

Lieber et al. reported both the total number of times a constraint type occurred and the percentage of projects in which it occurred at least once. Those measures are not computed in this milestone.

Rabbani et al. 2022 surveyed how people generate and adopt SHACL and ShEx, reviewed tools, and tried automatic shape extraction on large knowledge graphs. It is not a GitHub repository census and is not used as a discovery method here.

A search hit is not a verified SHACL repository. The candidate table is the set of repositories returned by the queries below.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Set `GITHUB_TOKEN` in the environment or in `.env`. The token is not read from source code. Code search requires authentication.

## Discover

From the repository root:

```bash
python -m shacl_study discover --dry-run
python -m shacl_study discover
```

`--dry-run` prints the planned queries and does not call GitHub. A saved run is resumed automatically. `--fresh` discards saved discovery state and starts again. `--query-id` limits execution to one planned query; if that repository query hits the result ceiling, its date partitions still run. `--max-pages` stops a query early and records `local_page_limit`. It does not trigger date partitioning.

`inspect`, `stats`, `audit`, and `run-all` are refused. `verify` inspects repository content at a pinned commit. A search hit is still not, by itself, a verified SHACL repository.

## Queries

The configuration is [config/discovery_queries.yaml](config/discovery_queries.yaml). Code search and repository search stay separate executions. A repository keeps every query id that returned it.

Code search, `GET /search/code`, sends:

- the SHACL namespace and the quoted `sh:` names and IRIs listed in the config, each crossed with `extension:` `ttl`, `trig`, `nt`, `rdf`, `xml`, `owl`, `jsonld`, and `nq`
- one broad `SHACL` query with no extension partition

Every code query sends `in:file`. Each one is planned twice: once with no fork qualifier, and once with `fork:only`. A live check showed that `fork:true` on this code-search endpoint returned the fork-only population, so code search does not use `fork:true`. Extension slices are an RDF-oriented partition, not a claim that SHACL only occurs in those extensions. Path partitioning is not used.

Repository search, `GET /search/repositories`, sends:

- `topic:shacl is:public fork:true`
- `SHACL in:name,description,readme,topics is:public fork:true`

The second query is metadata and README text. It is not code search. GitHub’s repository search does not search file contents, and a query without `in:` does not search README text, so the README field is stated in the query.

Repository search keeps `fork:true`, which in the pilot returned the broader repository set. `is_fork` and the parent repository fields come from repository metadata. Code-search provenance records the stream in `discovered_by` as `code:<family>:primary` or `code:<family>:fork_only`, and in `discovery_queries` as separate query ids. A repository found by both streams stays one row, keyed by GitHub repository id. No decision is made here about an analytical subset.

## Result ceiling

GitHub returns at most 1,000 search results per query. Repository queries that report at least 1,000 hits are not treated as a complete result. They are split on `created:` date ranges, from `2007-01-01` through the run’s window end, until a slice is under the ceiling or covers a single day. The unsplit query is stored with `api_status=split`, and its own hits are not copied into the candidate table. A single day that still reports at least 1,000 hits is stored as potentially truncated with `unsplittable_date_window`.

Code queries are not date-partitioned and are not path-partitioned. If a code query reports at least 1,000 hits, or GitHub sets `incomplete_results`, the retrieved pages are kept and the query is marked potentially truncated.

This is the set of repositories discoverable through these queries. It is not a complete list of GitHub repositories.

## Outputs

| file | contents |
| --- | --- |
| `data/results/discovery_queries.csv` | one row per query execution |
| `data/results/candidate_repositories.csv` | one row per public repository id |
| `data/results/nonpublic_hits.csv` | repositories visible to the token that are not public |
| `data/results/run_manifest.json` | timestamp, tool version, git commit, API version, config hash, Python and dependency versions |
| `data/candidates/discovery_state.json` | resume state |
| `data/raw/github-cache/` | cached JSON responses |
| `data/logs/discovery.log` | run log |

`discovered_by` and `discovery_queries` use `|` between values. `discovered_by` is `endpoint:query_family`.

Candidate columns are filled from search results and from `GET /repos/{owner}/{repo}`. Parent repository fields come from that repository call. Verification writes separate files under `data/results/` and does not change this candidate table. Inclusion decisions and constraint statistics are not part of verification.

## GitHub limits that bound the candidate set

Documented for the REST search API and for legacy code search, which is the syntax `GET /search/code` uses:

- 1,000 retrieved results per query
- authenticated search: 30 requests per minute, and 10 per minute for code search
- code search requires authentication
- code search indexes the default branch only
- code search indexes files smaller than 384 KB
- code search does not index archived repositories
- code search indexes a repository only if it had activity or was returned in search during the last year
- a fork is indexed for code search only if it has more stars than its parent and has at least one commit after creation
- legacy code search ignores a set of punctuation characters, including `:`, `/`, `#`, and `"`. The configured queries are still sent as quoted IRIs and `sh:` terms; the API documentation says those characters are not part of the match
- the search API may set `incomplete_results` when a query times out
- the REST search documentation also says a query searches up to 4,000 repositories matching its filters

`is:public` is a repository-search qualifier. It is not a documented legacy code-search qualifier, so code-search queries do not send it. After `GET /repos/{owner}/{repo}`, a repository that is not public is left out of `candidate_repositories.csv` and written to `nonpublic_hits.csv`.

## Tests

```bash
pytest
```

The tests use a fake GitHub client. They do not require a token.
