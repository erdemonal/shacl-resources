# Failure Case Feasibility Inventory

## Purpose

This file records whether the seven sources with **verified examples, tests, and stored validation outcomes** contain enough material for case-level analysis of SHACL validation failures.

The seven sources are **not treated as representative of all SHACL usage**. They are a feasibility subset selected from the 32-source corpus using the same material-availability criterion.

## Important methodological rule

The fields below record **what the source explicitly provides**. They do not infer a root cause when the source does not document one.

In particular:

- a SHACL validation result is not automatically a data defect;
- a file name such as `*-fail` is evidence of test intent, not necessarily a complete explanation;
- a test-harness failure must be distinguished from a SHACL validation failure;
- `partial` means some contextual evidence is available, but not enough to claim a fully documented underlying cause.

## Inventory

| Source | Example case | Negative fixture | Expected failure explicit | Stored outcome | Project-written explanation | Repair/fix documented | Use for case analysis |
|---|---|---:|---:|---:|---:|---:|---|
| SRC003 OGC Building Blocks | feature-missing-type-fail.json; feature-bad-link-fail.ttl; feature-point-no-coordinates-fail.ttl | yes | yes | yes | partial | not verified | yes |
| SRC006 ODCT | modifieddataset1.json; modifieddataset2.json; modifieddataset3.json | yes | yes | yes | yes | not verified | yes |
| SRC012 IndustryFusion Process Data Twin | expected-divergences.txt; SHACL2Flink/PySHACL comparison fixtures | yes | yes | yes | yes | partial | yes |
| SRC023 BuildingMOTIF | model validation tutorial; missing heating coil required by a manifest | yes | yes | yes | yes | yes | yes |
| SRC024 Unified Cyber Ontology | *_PASS.json; *_XFAIL.json; *_validation.ttl | yes | yes | yes | yes | not verified | yes |
| SRC030 Cube Schema | invalid.withoutProperties.ttl and approved validation output | yes | yes | yes | partial | not verified | yes |
| SRC032 CRS Ontology | axisDirection-fail.ttl; generated test report | yes | yes | yes | partial | not verified | yes_with_caution |

## Source-specific notes

### SRC003 — OGC Building Blocks

The test report marks failing fixtures with requireFail=true. File names often encode the intended defect, but this should not be treated as a full root-cause explanation unless prose documentation is also present.

### SRC006 — ODCT

The Zenodo record explicitly states that the modified datasets introduce type mismatches, spelling errors, extraneous properties, missing required properties, and additional priority levels. Separate compliance reports are provided.

### SRC012 — IndustryFusion Process Data Twin

The project documents deliberate divergences from PySHACL and explains why particular differences are accepted. Examples include RDF-list representation effects, lexical/type handling, and different constraint-component reporting. These explanations are project interpretations and should not be generalized beyond the documented cases.

### SRC023 — BuildingMOTIF

The tutorial explains why the model fails, adds the missing heating coil, reconnects it to the AHU, and validates again. The documentation also distinguishes ontology correctness from semantic sufficiency for a use case.

### SRC024 — Unified Cyber Ontology

The README states that XFAIL data are modified to trigger validation errors and documents several test-case combinations. This provides explicit test intent, but not every validation result necessarily has a prose explanation of the underlying real-world cause.

### SRC030 — Cube Schema

Approved outputs preserve SHACL result structure and human-readable messages, including nested details. This is strong evidence for constraint-level explanation, but it should not automatically be treated as provenance of why the bad input arose.

### SRC032 — CRS Ontology

The generated report contains expected-fail metadata and SHACL outputs. At least one fixture is marked requireFail=true while SHACL reports conforms=true, causing the test harness itself to fail. Therefore test-harness failure and SHACL validation failure must be kept separate.

## What this inventory can support

At this stage, the inventory supports only a **feasibility claim**:

> Some sources in the collected corpus provide enough material to compare a SHACL validation outcome with the test intent and surrounding documentation.

It does **not** yet support claims about:

- how SHACL projects generally document failures;
- how common any explanation type is;
- a final taxonomy of failure causes;
- whether a validation failure is a data error, constraint error, or other category unless the source explicitly says so;
- novelty of a research contribution.

## Next analysis step

For each usable source, extract individual documented failure cases with the following fields:

1. failing input or fixture;
2. expected outcome;
3. actual SHACL outcome;
4. source constraint component and result path when available;
5. explicit project explanation, if any;
6. documented correction or repair, if any;
7. evidence location;
8. researcher note restricted to factual comparison, separated from source-provided explanation.

Only after this case inventory is populated should recurring patterns be compared.
