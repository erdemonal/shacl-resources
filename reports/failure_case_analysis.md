# Failure Case Analysis

## Purpose

This file performs a **case-level follow-up** to `failure_case_feasibility_inventory.md`.

The goal is not to create a final taxonomy of SHACL failure causes. It is to record what the selected sources explicitly document around individual validation cases, and then check whether **recurring evidence patterns** appear across sources.

The seven sources were selected because the material-availability assessment verified examples, tests, and stored validation outcomes for each of them. They are a **feasibility subset**, not a representative sample of all SHACL usage.

## Method

For each inspected case, the following were recorded when available:

- failing input or fixture;
- expected outcome;
- actual validation outcome;
- source constraint component and result path;
- project-provided explanation;
- documented correction or repair;
- evidence location.

No root cause was inferred when the source did not explicitly document one.

### Observed evidence patterns

These codes describe **types of evidence found in the inspected material**. They are not proposed as a taxonomy of SHACL failure causes.

- **P1** — Explicit test intent or seeded invalid input
- **P2** — Constraint-level diagnostic evidence in a stored validation result
- **P3** — Human/project explanation beyond the raw validation result
- **P4** — Documented correction or repair followed by re-validation
- **P5** — Mismatch/divergence between validator output, implementation semantics, or test expectation

## Case inventory

| Case | Source | Fixture / case | Expected | Actual | Explicit project explanation | Pattern |
|---|---|---|---|---|---|---|
| C001 | SRC003 OGC Building Blocks | `feature-bad-link-fail.ttl` | fail | SHACL conforms=false | Test is explicitly marked as expected to fail; SHACL report says the value does not conform to geojson:LinkShape. | P1;P2 |
| C002 | SRC003 OGC Building Blocks | `feature-point-no-coordinates-fail.ttl` | fail | SHACL conforms=false | Test is explicitly marked as expected to fail; report says the geometry value does not conform to geojson:GeometryShape. | P1;P2 |
| C003 | SRC006 ODCT | `modifieddataset1.json` | non-compliant | 68% compliant properties; 73.33% compliant constraints | The dataset intentionally introduces type mismatches and spelling errors. | P1;P3 |
| C004 | SRC006 ODCT | `modifieddataset2.json` | non-compliant / partially unchecked | 79.31% compliant properties; 93.33% compliant constraints; some items not checked | The dataset intentionally contains extraneous properties and missing required properties. | P1;P3 |
| C005 | SRC006 ODCT | `modifieddataset3.json` | non-compliant / partially unchecked | 53.57% compliant properties; 66.67% compliant constraints; non-compliant and unchecked items reported | The dataset intentionally includes extraneous and missing properties and additional priority levels. | P1;P3 |
| C006 | SRC012 IndustryFusion Process Data Twin | `test22/model3.jsonld` | documented deliberate divergence from PySHACL | PySHACL reports NodeKindConstraintComponent; project intentionally does not | An empty RDF list becomes rdf:nil, which is an IRI. The project states that the resulting SHACL node-kind violation is a representation artefact rather than something wrong with the data. | P3;P5 |
| C007 | SRC012 IndustryFusion Process Data Twin | `test5/model1.jsonld and test5/model2.jsonld` | documented deliberate divergence from PySHACL | PySHACL reports range violations for numeric values represented as strings; project intentionally parses lexical values | The project says numeric strings are ordinary correct NGSI-LD data in its context and deliberately stays more relaxed than SHACL's declared-type comparison. | P3;P5 |
| C008 | SRC012 IndustryFusion Process Data Twin | `test9/model2.jsonld; test9/model6.jsonld; test16/model2.jsonld; test19/model3.jsonld` | same underlying failure may be named differently | PySHACL reports wrapper components while project reports more specific inner components | The project explains that flattening the shape tree changes which component names the alert, although the underlying failing attribute is the same. | P3;P5 |
| C009 | SRC023 BuildingMOTIF | `model validation tutorial — manifest validation` | model should satisfy manifest requirements | model invalid because required heating coil is missing | The tutorial explicitly says one reason for failure is that the required heating coil was forgotten. | P3;P4 |
| C010 | SRC023 BuildingMOTIF | `model validation tutorial — Guideline 36 use-case validation` | AHU should satisfy single-zone VAV requirements | validation fails because required points are missing | The tutorial states that the AHU does not have the required points and contrasts the official SHACL report with BuildingMOTIF's easier-to-understand interpretation. | P3 |
| C011 | SRC024 Unified Cyber Ontology | `location_XFAIL` | fail | SHACL conforms=false; three ValidationResults stored | The README states XFAIL examples are modified to trigger shape validation errors. The stored report says two hasFacet values do not have class core:Facet and postalCode is integer rather than xsd:string. | P1;P2 |
| C012 | SRC030 Cube Schema | `invalid.withoutProperties.ttl` | fail | SHACL conforms=false | The approved report states that the Cube must point to a valid Constraint and that the Constraint needs at least a certain amount of sh:properties (minCount 3). | P1;P2 |
| C013 | SRC032 CRS Ontology | `axisDirection-fail.ttl` | fail | SHACL conforms=true; test harness reports 'expected to fail but it did not' | Generated report records the mismatch between the expected failing test and the SHACL result. | P5 |
| C014 | SRC032 CRS Ontology | `coordinateSystemAxis.ttl` | not marked requireFail | SHACL conforms=false | Generated SHACL result message says 'A coordinate system should have at least one axis'. | P2;P5 |

## Recurring-pattern check

### P1 — Explicit test intent or seeded invalid input

Observed in **7 inspected case(s)** across **4 source(s)**: SRC003, SRC006, SRC024, SRC030.

Several repositories deliberately publish invalid or expected-failing fixtures. This provides evidence about **test intent**, but does not by itself provide a full explanation of why an analogous failure would occur in production data.

### P2 — Constraint-level diagnostic evidence in a stored validation result

Observed in **5 inspected case(s)** across **4 source(s)**: SRC003, SRC024, SRC030, SRC032.

Stored SHACL reports commonly identify structural details such as the constraint component, result path, source shape, value, or human-readable message. This is useful diagnostic evidence, but it remains primarily a description of **what constraint failed**.

### P3 — Human/project explanation beyond the raw validation result

Observed in **8 inspected case(s)** across **3 source(s)**: SRC006, SRC012, SRC023.

Some projects add prose or application-specific interpretation that goes beyond the raw SHACL result. The strongest inspected examples are IndustryFusion, BuildingMOTIF, and ODCT.

### P4 — Documented correction or repair followed by re-validation

Observed in **1 inspected case(s)** across **1 source(s)**: SRC023.

A complete failure → correction → re-validation sequence was verified only in the inspected BuildingMOTIF tutorial. On the present evidence this should not be presented as a recurring cross-project practice.

### P5 — Mismatch/divergence between validator output, implementation semantics, or test expectation

Observed in **5 inspected case(s)** across **2 source(s)**: SRC012, SRC032.

The inspected material contains cases where validation/reporting behaviour differs from project expectations or application semantics. IndustryFusion documents deliberate implementation divergences; CRS records expected-fail and unexpected-fail mismatches. These are not all the same phenomenon, so they should remain separate case types rather than being collapsed into one causal category.

## Result

The case inspection supports a **limited recurring observation**:

> Public SHACL test resources can contain several layers of evidence around a failure: test intent, structural validation diagnostics, and sometimes project-specific explanation. These layers are not equivalent.

The inspected cases repeatedly show a distinction between:

1. **what was expected to fail**;
2. **what the validator reported**; and
3. **how the project interprets that result**.

This distinction is visible across multiple sources, but the present subset does **not** justify a general taxonomy of SHACL failure causes.

### Important negative result

The cases do **not** support the simple claim that every validation failure can be classified from the validation report alone as a data error, constraint error, or context error.

Reasons include:

- some fixtures only document expected failure and the violated constraint;
- some projects supply additional prose context;
- IndustryFusion explicitly treats some PySHACL findings as representation or application-semantics issues rather than data defects;
- CRS contains mismatches between test expectation and SHACL conformance;
- OGC's test pipeline can fail at a non-SHACL validation stage (for example JSON Schema), so pipeline failures must not automatically be counted as SHACL violations.

## What this means for scope

The strongest supported direction is **not** “build a taxonomy of SHACL errors” at this stage.

A more defensible question to discuss with supervisors is whether the project should study the **evidence available for interpreting expected validation failures**, for example:

> What information published with SHACL test cases is available to distinguish test intent, validator findings, and project interpretation?

This remains a **candidate direction**, not a final research question or novelty claim.

The alternative shape/profile comparison direction remains separate and should not be merged into this analysis without a clear reason.

## Stop condition for this exploratory phase

For the current narrowing phase, the objective has been met:

- the 32-source corpus has been collected and screened;
- material availability has been assessed;
- a reproducible seven-source feasibility subset has been identified;
- individual cases have been inspected;
- recurring evidence patterns and counterexamples have been recorded;
- the analysis does not require additional source collection before supervisor discussion.

Further expansion of the case set should be driven by the research question chosen with the supervisors, rather than by continued open-ended exploration.
