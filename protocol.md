# Collection Protocol

## Purpose

This repository collects SHACL resources together with the ontologies, specifications, profiles, examples, and test files associated with them.

The goal is to build a reproducible collection that can be used to study how SHACL is used in different projects and standardization efforts.

The collection is currently exploratory. It does not assume a research gap or a fixed research question. The material collected here will first be examined to determine which questions can be studied with sufficient evidence.

## Scope

The collection covers publicly available SHACL resources that can be linked to a known ontology, specification, application profile, project, or validation task.

Both manually written and generated SHACL shapes may be included.

Sources may come from standards organizations, ontology projects, research projects, public repositories, and other documented initiatives.

Priority is given to resources for which there is enough documentation to understand what the shapes are meant to validate.

## Inclusion criteria

A resource may be included if:

- the SHACL shapes are publicly available;
- the project, organization, or initiative responsible for the resource can be identified;
- the validation target can be identified, such as an ontology, specification, profile, or data model;
- the purpose of the shapes can be established from documentation, a specification, a publication, repository material, or another traceable source;
- the resource can be referenced through a version, release, commit, persistent identifier, or retrieval date.

Example data and test cases are not required, but their presence or absence is recorded.

A resource does not need to be an official standards artifact. Its authoritative status is recorded separately.

Each source receives an explicit screening decision: `candidate`, `included`, or `excluded`. Excluded sources retain an exclusion reason.

## Exclusion criteria

A resource will normally be excluded if:

- it is only a tutorial or isolated example with no clear source or validation purpose;
- the SHACL fragment cannot be linked to an identifiable project, specification, ontology, or profile;
- it is a duplicate or mirror of an artifact already recorded;
- it is not publicly accessible;
- there is not enough information to determine what the shapes are meant to validate.

Potentially relevant resources that cannot yet be verified are kept as candidates instead of being discarded.

## Discovery strategy

Resources are collected through several routes.

The initial set includes sources suggested during project discussions and resources found during preliminary work.

Additional resources are identified through:

- standards and specification organizations;
- ontology and vocabulary repositories;
- public source code repositories;
- surveys and review papers on SHACL;
- references in relevant publications;
- working groups and community initiatives;
- links from SHACL projects already included in the collection.

Each discovery action is recorded in `data/discovery_log.csv`, including the route, platform, query or seed, date, and screening counts.

The discovery process may be extended if additional useful source types are identified.

## Metadata

Metadata is recorded at two levels: sources and artifacts.

### Sources

A source represents a project, organization, standard, or initiative from which one or more artifacts originate.

For each source, the repository records fields such as:

- name;
- organization;
- source type;
- homepage;
- repository;
- discovery method;
- discovery date;
- screening decision;
- exclusion reason, when excluded;
- notes.

### Artifacts

An artifact represents a specific file or resource, such as a specification, ontology, SHACL shapes graph, profile, example dataset, test dataset, or documentation page.

For each artifact, the repository records fields such as:

- artifact type;
- source;
- name;
- version;
- URL;
- repository path;
- release or commit;
- retrieval date;
- file format;
- authoritative status;
- validation target;
- profile name, where relevant;
- whether the artifact is manually written or generated, when known;
- availability of examples and tests;
- license;
- local path;
- notes.

Missing information is recorded as unknown rather than inferred.

## Artifact collection

After a source is included, artifacts are collected from one fixed reference snapshot of that source.

A current stable or recommended release is preferred when one exists. If no such release is available, an exact repository commit or a persistent record such as a DOI is used instead.

Within the selected snapshot, all artifacts that fall within the collection scope are recorded. Artifacts are not selected because they appear interesting for a possible research question.

The initial collection scope covers:

- SHACL shapes;
- ontology or vocabulary artifacts;
- specification or profile documents needed to identify the validation target;
- example RDF data;
- test RDF data;
- validation reports;
- documentation that explains the SHACL artifact or its intended target.

Material that is not part of this scope, such as build logs, logos, stylesheets, or other website assets, is not recorded as corpus artifacts.

Historical versions are not collected during the initial pilot unless they are needed to identify or interpret the selected artifact. If later analysis shows that version comparison is research-worthy, the protocol can be extended for that purpose.

If a source exposes a machine-readable registry, all qualifying entries are enumerated from that registry rather than selected manually. For example, when a register lists building blocks with associated SHACL shapes, every entry with a non-empty SHACL field in the fixed register snapshot is recorded.

## Versioning and provenance

Version information is recorded whenever it is available.

Depending on the source, this may be:

- an ontology or specification version;
- a software release;
- a Git commit;
- a repository tag;
- a persistent identifier;
- a publication version.

If no stable version is available, the retrieval date is recorded instead.

The original source URL is preserved, together with the repository path or commit when relevant.

Checksums may later be added for downloaded artifacts to make it possible to verify the exact retrieved file.

## Duplicate handling

Duplicates are checked at both the source and artifact levels.

A mirror, copied file, or redistributed version of an existing artifact is not treated as a separate resource by default.

Different versions of the same artifact may be kept as separate records when version comparison is relevant.

If the same SHACL shapes are available from several locations, the main record should point to the original or authoritative source when this can be determined. Other locations may be recorded as alternatives.

## Reproducibility

The repository should make it possible to determine:

- where each resource came from;
- when it was retrieved;
- which version or commit was used;
- what it was meant to validate;
- how it entered the collection.

The CSV manifests are checked automatically for structural consistency.

Scripts may later be added for downloading artifacts and performing structural analysis. Automated discovery, however, will not replace manual verification of provenance and validation purpose.

Any change to the protocol that affects inclusion, exclusion, or required metadata should be recorded in the repository history.