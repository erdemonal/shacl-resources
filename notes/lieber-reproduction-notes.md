# Lieber et al. 2020 and the supplied archive

This note records differences that were observed between the poster and the archive supplied in this repository. It does not explain those differences.

The poster states that the corpus and the download tool are available at <https://zenodo.org/record/3988930>. The file examined here is `montolo-shape-stats(1).zip`. This note does not re-download that Zenodo record, and it does not establish that the zip is a byte-for-byte copy of the record.

## What the paper reports

Lieber et al., “Statistics about Data Shape Use in RDF Data” (`paper584.pdf`), report the following:

- GitHub was searched for the term “SHACL”.
- Repositories were manually selected when they contained valid SHACL shapes that did not appear as simple examples.
- Common SHACL shapes were also considered, including Schema.org’s SHACL and the SHACL constraints of SHACL itself.
- The SHACL RDF files of 13 projects, containing 1,978 NodeShapes, were analyzed.
- Two of those projects are described as generated shapes: OSLO and the SHACL version of schema.org.

The poster does not name the 13 projects, does not define how a NodeShape was counted, and does not give an operational definition of “simple examples”.

## What the supplied archive contains

`montolo-shape-stats(1).zip` contains `data/README.txt`, `data/get-content.js`, three download configs, and N-Triples dumps.

`download-config/curated-shapes.json` has 19 entries:

- 11 with `type: git`
- 6 with `type: file-url`
- 2 with `type: file-local` (`dcat-de` and `hiphop`). Their descriptions call them fixed copies.

`download-config/oslo-shapes.json` has one `type: git` entry. `download-config/schema-shapes.json` has one `type: file-url` entry, `http://datashapes.org/schema.ttl`.

The raw directories contain 21 `.nt` files: 19 under `raw-curated`, plus `raw-oslo/oslo.nt` and `raw-schemash/schemash.nt`.

For `type: git`, `get-content.js` clones the configured ref (`master` when `ref` is absent; the OSLO config sets `circleci`) and reads `**/*.ttl` under the configured folders only. A Turtle file that fails parsing is left out of the merged N-Triples file. The script does not rewrite file text. `data/README.txt` states that a Turtle file with a syntax error was downloaded manually, using the `file-local` config key. The configs do not record a commit SHA.

## What direct counting produced

Each count below is the number of N-Triples lines whose predicate is `http://www.w3.org/1999/02/22-rdf-syntax-ns#type` and whose object is `http://www.w3.org/ns/shacl#NodeShape`. This is not a reimplementation of Montolo.

| file | explicit `sh:NodeShape` triples |
| --- | ---: |
| aksw-sh.nt | 14 |
| bds.nt | 30 |
| dcat-ap.nt | 28 |
| dcat-de.nt | 2 |
| dcat-ech.nt | 6 |
| eli-sh.nt | 77 |
| eudm.nt | 8 |
| fair.nt | 5 |
| fsgim.nt | 552 |
| geo.nt | 35 |
| geovalidator.nt | 13 |
| hiphop.nt | 16 |
| oash.nt | 13 |
| periodo.nt | 7 |
| scolomfr-sh.nt | 2 |
| shsh.nt | 10 |
| tern.nt | 5 |
| uwl.nt | 36 |
| wasa.nt | 12 |
| curated total | 871 |
| oslo.nt | 536 |
| schemash.nt | 843 |
| all supplied dumps | 2250 |

## Discrepancy

The poster reports 13 projects and 1,978 NodeShapes. The supplied archive contains 21 N-Triples dumps and 2,250 explicit `rdf:type sh:NodeShape` triples under the count above. Nothing in the poster or in `data/README.txt` identifies a subset of these files as the source of 1,978. The reason for the difference is unresolved.
