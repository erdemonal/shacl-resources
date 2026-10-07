# Milestone 1 candidate evidence cohorts

Local counts from `data/results/candidate_repositories.csv`. No GitHub API calls were made. These repositories are discovery candidates. They are not verified SHACL repositories.

The discovery run finished at 2026-10-07T18:04:03Z. It recorded git commit `b473b5b018db712b34f815f762f0c1ff740c22a6`, `git_dirty: true`, and discovery config SHA-256 `0f74130f2ce444f77644f39dbf84f9fe70126cba49ea3116a1647f19e8952774`.

The candidate file has 15,075 rows, one per GitHub repository id. Provenance comes from `discovered_by`. A code-search label keeps its stream (`primary` or `fork_only`); both streams count as the same evidence family below. `code:broad_text` and `repository:broad_text` stay separate families.

## Mutually exclusive partition

A repository is in exactly one of these four groups. The four counts sum to 15,075.

`CODE_SIGNAL_ONLY` means at least one code-search family and no repository-search family. The inclusive code-search set, which also contains `MULTIPLE_EVIDENCE`, is 2,908 repositories (19.29%).

| cohort | repositories | share | non-forks | forks | archived | median stars |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CODE_SIGNAL_ONLY | 1,818 | 12.06% | 884 | 934 | 0 | 0 |
| TOPIC_ONLY | 229 | 1.52% | 226 | 3 | 13 | 1 |
| BROAD_REPOSITORY_ONLY | 11,938 | 79.19% | 4,569 | 7,369 | 143 | 0 |
| MULTIPLE_EVIDENCE | 1,090 | 7.23% | 674 | 416 | 0 | 0 |

`TOPIC_ONLY` is topic search with no code-search hit. All 229 of those repositories also have `repository:broad_text`. None were found by the topic query alone.

`BROAD_REPOSITORY_ONLY` is `repository:broad_text` with neither a code-search hit nor `topic:shacl`.

`MULTIPLE_EVIDENCE` is at least one code-search family and at least one repository-search family.

Archived counts are 0 in both cohorts that include a code-search hit. Code search does not index archived repositories, so an archived repository can enter this candidate file only through repository search.

## Additional counts

| item | repositories | share of 15,075 |
| --- | ---: | ---: |
| A. At least one targeted code family, excluding `code:broad_text` | 2,607 | 17.29% |
| B. Only `code:broad_text` | 145 | 0.96% |
| C. Only `repository:broad_text` | 11,938 | 79.19% |
| D. `canonical_namespace` | 1,086 | 7.20% |
| E. A `sh:NodeShape` or `sh:PropertyShape` query | 1,194 | 7.92% |

Targeted code families are `canonical_namespace`, `shacl_class_name`, `shacl_term`, and `shacl_full_iri`. Row E is the `shacl_class_name` family. That family is the `sh:NodeShape` and `sh:PropertyShape` queries.

## Distinct evidence families

The seven families are `canonical_namespace`, `shacl_class_name`, `shacl_term`, `shacl_full_iri`, `code_broad_text`, `repository_topic`, and `repository_broad_text`. Primary and fork-only streams are not counted as separate families.

| distinct families | repositories | share |
| --- | ---: | ---: |
| 1 | 12,966 | 86.01% |
| 2 | 1,069 | 7.09% |
| 3 | 534 | 3.54% |
| 4 | 336 | 2.23% |
| 5 | 151 | 1.00% |
| 6 | 18 | 0.12% |
| 7 | 1 | 0.01% |

Four or more families: 506 repositories (3.36%).

## Overlap

Each cell is the number of candidate repositories that carry both families. The diagonal is the size of that family. `repository_topic` is entirely inside `repository_broad_text` (346 of 346).

|  | namespace | class name | term | full IRI | code broad | topic | repo broad |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| canonical_namespace | 1,086 | 616 | 760 | 162 | 210 | 41 | 399 |
| shacl_class_name | 616 | 1,194 | 1,114 | 92 | 227 | 71 | 560 |
| shacl_term | 760 | 1,114 | 2,149 | 142 | 292 | 95 | 820 |
| shacl_full_iri | 162 | 92 | 142 | 261 | 38 | 17 | 103 |
| code_broad_text | 210 | 227 | 292 | 38 | 627 | 31 | 352 |
| repository_topic | 41 | 71 | 95 | 17 | 31 | 346 | 346 |
| repository_broad_text | 399 | 560 | 820 | 103 | 352 | 346 | 13,257 |
