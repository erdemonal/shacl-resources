# Query sanity pilot

Authenticated page-1 check of seven discovery queries. This does not verify SHACL and does not decide corpus inclusion.

Collected at 2026-10-07T13:17:42Z. Each search requested page 1 with per_page=20. File and metadata checks use the first 15 results in GitHub best-match order.

| query_id | query | reported_total | sample_checked | sample_with_intended_literal | sample_without_intended_literal | notes |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| code__canonical_namespace__ext_ttl | `"http://www.w3.org/ns/shacl#" in:file fork:true extension:ttl` | 21568 | 15 | 15 | 0 | total_count is at or above 1000; 20/20 fetched are forks |
| code__class_node_shape__ext_ttl | `"sh:NodeShape" in:file fork:true extension:ttl` | 10688 | 15 | 15 | 0 | total_count is at or above 1000; 20/20 fetched are forks |
| code__class_property_shape__ext_ttl | `"sh:PropertyShape" in:file fork:true extension:ttl` | 4240 | 15 | 15 | 0 | total_count is at or above 1000; 20/20 fetched are forks |
| code__term_target_class__ext_ttl | `"sh:targetClass" in:file fork:true extension:ttl` | 6288 | 15 | 15 | 0 | total_count is at or above 1000; 20/20 fetched are forks |
| code__broad_shacl | `SHACL in:file fork:true` | 127232 | 15 | 15 | 0 | total_count is at or above 1000; 20/20 fetched are forks |
| repository__topic_shacl | `topic:shacl is:public fork:true` | 346 | 15 | 15 | 0 | under the 1000 ceiling; 0/20 fetched are forks |
| repository__broad_shacl | `SHACL in:name,description,readme,topics is:public fork:true` | 13250 | 15 | 15 | 0 | total_count is at or above 1000; 0/20 fetched are forks |

## Rate limits

- resource `code_search`: limit 10, remaining 9 after a 200 response on `code`
- resource `core`: limit 5000, remaining 4970 after a 200 response on `core`
- resource `search`: limit 30, remaining 29 after a 200 response on `repository`

## Forks

- `code__canonical_namespace__ext_ttl`: 20 of 20 fetched results are forks.
- `code__class_node_shape__ext_ttl`: 20 of 20 fetched results are forks.
- `code__class_property_shape__ext_ttl`: 20 of 20 fetched results are forks.
- `code__term_target_class__ext_ttl`: 20 of 20 fetched results are forks.
- `code__broad_shacl`: 20 of 20 fetched results are forks.
- `repository__topic_shacl`: 0 of 20 fetched results are forks.
- `repository__broad_shacl`: 0 of 20 fetched results are forks.
- Extra probe `topic:shacl is:public fork:only`: total_count=3, fetched=3, forks_in_fetched=3.

## Samples

### code__canonical_namespace__ext_ttl

endpoint `code`; incomplete_results=False; ceiling_relevant=True; fetched=20.

- literal fork `iop-alliance/OpenKnowHow:src/spec/okh_proposed.ttl` — full SHACL namespace IRI
  - highlighted: @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> . @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> . @prefix schema: <http://schema.org/> . @prefix sh: <http://www.
- literal fork `HuygensING/shaclex:examples/shex/or.ttl` — full SHACL namespace IRI
  - highlighted: prefix : <http://example.org/> prefix sh: <http://www.w3.org/ns/shacl#> :x1 :p :y ; :q :z . :x2 :p :y . :x3 :q :y . :x4 :r 1 .
- literal fork `HuygensING/shaclex:examples/manifest.ttl` — full SHACL namespace IRI
  - highlighted: @prefix mf: <http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#> . @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> . @prefix rdfs: <http://www.w3.org/2000/01/rdf-
- literal fork `HuygensING/shaclex:examples/shex/not.ttl` — full SHACL namespace IRI
  - highlighted: prefix : <http://example.org/> prefix sh: <http://www.w3.org/ns/shacl#> :x1 :q :z . :x2 :p :y . :S sh:targetNode :x1 .
- literal fork `HuygensING/shaclex:examples/shex/any.ttl` — full SHACL namespace IRI
  - highlighted: prefix : <http://example.org/> prefix sh: <http://www.w3.org/ns/shacl#> :x1 :p :y . :S sh:targetNode :x1 .
- literal fork `HuygensING/shaclex:examples/shex/and.ttl` — full SHACL namespace IRI
  - highlighted: prefix : <http://example.org/> prefix sh: <http://www.w3.org/ns/shacl#> :x1 :p :y ; :q :z . :x2 :p :y . :x3 :q :y .
- literal fork `HuygensING/shaclex:examples/shex/base.ttl` — full SHACL namespace IRI
  - highlighted: prefix sh: <http://www.w3.org/ns/shacl#> base <http://example.org/> <x> <p> 1 .
- literal fork `HuygensING/shaclex:examples/shex/rbe1.ttl` — full SHACL namespace IRI
  - highlighted: prefix : <http://example.org/> prefix sh: <http://www.w3.org/ns/shacl#> :x1 :p :y ; :p [:p :z]; :q :z; :r 1 .
- literal fork `HuygensING/shaclex:examples/shex/not1.ttl` — full SHACL namespace IRI
  - highlighted: prefix : <http://example.org/> prefix sh: <http://www.w3.org/ns/shacl#> :x1 :p 1 . # It fails...but maybe, it shouldn't ? :x2 :p 1; :q 7 . # OK :x3 :p 1; :q 4 . # Must fail :x4 :p 
- literal fork `HuygensING/shaclex:examples/shex/not2.ttl` — full SHACL namespace IRI
  - highlighted: prefix : <http://example.org/> prefix sh: <http://www.w3.org/ns/shacl#> :x1 :p 1 . :x2 :q 1; :r 2 . # OK :x3 :p 1; :r 2 . # OK
- literal fork `HuygensING/shaclex:examples/shacl/xone.ttl` — full SHACL namespace IRI
  - highlighted: prefix : <http://example.org/> prefix sh: <http://www.w3.org/ns/shacl#> prefix xsd: <http://www.w3.org/2001/XMLSchema#> prefix schema: <http://schema.org/> prefix foaf: <http://xml
- literal fork `HuygensING/shaclex:examples/shex/good1.ttl` — full SHACL namespace IRI
  - highlighted: prefix : <http://example.org/> @prefix sh: <http://www.w3.org/ns/shacl#> :x :p :y . :S sh:targetNode :x .
- literal fork `HuygensING/shaclex:examples/shacl/bad1.ttl` — full SHACL namespace IRI
  - highlighted: @prefix : <http://example.org/> @prefix sh: <http://www.w3.org/ns/shacl#> :S a sh:NodeShape; sh:targetNode :x; sh:property [ sh:path :p;
- literal fork `HuygensING/shaclex:examples/shex/someOf.ttl` — full SHACL namespace IRI
  - highlighted: prefix : <http://example.org/> prefix sh: <http://www.w3.org/ns/shacl#> :x :p 1 . :y :q 1 . :S sh:targetNode :y .
- literal fork `HuygensING/shaclex:examples/shacl/good9.ttl` — full SHACL namespace IRI
  - highlighted: @prefix : <http://example.org/> @prefix sh: <http://www.w3.org/ns/shacl#> @prefix xsd: <http://www.w3.org/2001/XMLSchema#> @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> :S 

### code__class_node_shape__ext_ttl

endpoint `code`; incomplete_results=False; ceiling_relevant=True; fetched=20.

- literal fork `sparqlunicorn/sparqlunicornGoesGIS:validation/geosparql11_validation.ttl` — sh:NodeShape
  - highlighted: <S1-cefaultGeometry-hasSerialization> a sh:NodeShape ; sh:targetObjectsOf geo:defaultGeometry ; | <S10-many-dimension-one> a sh:NodeShape ; sh:property <S10-many-dimension-one-sub> ;
- literal fork `netwerk-digitaal-erfgoed/lod-aggregator:shapes/shacl_edm.ttl` — sh:NodeShape
  - highlighted: ex:ProvidedCHO a sh:NodeShape ; sh:targetClass edm:ProvidedCHO ; | ex:Aggregation a sh:NodeShape ; sh:targetClass ore:Aggregation ;
- literal fork `HuygensING/shaclex:examples/shacl/xone.ttl` — sh:NodeShape
  - highlighted: :UserShape a sh:NodeShape ; sh:xone ( | :NotUserShape a sh:NodeShape ; sh:not :UserShape .
- literal fork `HuygensING/shaclex:examples/shacl/bad1.ttl` — sh:NodeShape
  - highlighted: @prefix : <http://example.org/> @prefix sh: <http://www.w3.org/ns/shacl#> :S a sh:NodeShape; sh:targetNode :x; sh:property [ sh:path :p;
- literal fork `HuygensING/shaclex:examples/shacl/good9.ttl` — sh:NodeShape
  - highlighted: @prefix xsd: <http://www.w3.org/2001/XMLSchema#> @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> :S a sh:NodeShape; sh:targetNode :x ; sh:property [ sh:path :p;
- literal fork `HuygensING/shaclex:examples/shacl/path1.ttl` — sh:NodeShape
  - highlighted: @prefix xsd: <http://www.w3.org/2001/XMLSchema#> @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> :S a sh:NodeShape, rdfs:Class ; sh:property [ sh:path [ sh:inversePath :p ]; 
- literal fork `HuygensING/shaclex:examples/shacl/good6.ttl` — sh:NodeShape
  - highlighted: @prefix xsd: <http://www.w3.org/2001/XMLSchema#> @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> :S a sh:NodeShape; sh:targetNode :x ; sh:property [ sh:path :p;
- literal fork `HuygensING/shaclex:examples/shacl/good3.ttl` — sh:NodeShape
  - highlighted: @prefix : <http://example.org/> @prefix sh: <http://www.w3.org/ns/shacl#> :S a sh:NodeShape; sh:targetNode :x, :y, :z ; sh:property [ sh:path :p;
- literal fork `HuygensING/shaclex:examples/shacl/good5.ttl` — sh:NodeShape
  - highlighted: :S a sh:NodeShape; sh:targetNode :x ; | ] . :T a sh:NodeShape; sh:property [
- literal fork `HuygensING/shaclex:examples/shacl/good4.ttl` — sh:NodeShape
  - highlighted: @prefix sh: <http://www.w3.org/ns/shacl#> @prefix xsd: <http://www.w3.org/2001/XMLSchema#> :S a sh:NodeShape; sh:targetNode :x, :y, :z, <t> ; sh:property [ sh:path :p;
- literal fork `HuygensING/shaclex:examples/shacl/good1.ttl` — sh:NodeShape
  - highlighted: @prefix : <http://example.org/> @prefix sh: <http://www.w3.org/ns/shacl#> :S a sh:NodeShape; sh:targetNode :x, :y ; sh:property [ sh:path :p;
- literal fork `HuygensING/shaclex:examples/shacl/good8.ttl` — sh:NodeShape
  - highlighted: @prefix xsd: <http://www.w3.org/2001/XMLSchema#> @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> :S a sh:NodeShape; sh:targetNode :x ; sh:property [ sh:path :p;
- literal fork `HuygensING/shaclex:examples/shacl/good2.ttl` — sh:NodeShape
  - highlighted: @prefix : <http://example.org/> @prefix sh: <http://www.w3.org/ns/shacl#> :S a sh:NodeShape; sh:targetNode :x, :y, :z ; sh:property [ sh:path :p;
- literal fork `HuygensING/shaclex:examples/shacl/loop1.ttl` — sh:NodeShape
  - highlighted: :S a sh:NodeShape ; sh:targetNode :x ; | :arrayShape a sh:NodeShape ; sh:property [
- literal fork `HuygensING/shaclex:examples/shacl/good7.ttl` — sh:NodeShape
  - highlighted: @prefix xsd: <http://www.w3.org/2001/XMLSchema#> @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> :S a sh:NodeShape; sh:targetNode :x ; sh:property [ sh:path :p;

### code__class_property_shape__ext_ttl

endpoint `code`; incomplete_results=False; ceiling_relevant=True; fetched=20.

- literal fork `sparqlunicorn/sparqlunicornGoesGIS:validation/geosparql10_validation.ttl` — sh:PropertyShape
  - highlighted: <S1-a-hasGeometry-hasSerialization-sub> a sh:PropertyShape ; sh:path [ | <S1-b-hasGeometry-hasSerialization-sub> a sh:PropertyShape ; sh:path geo:asWKT ;
- literal fork `sparqlunicorn/sparqlunicornGoesGIS:validation/geosparql11_validation.ttl` — sh:PropertyShape
  - highlighted: <S1-c-hasGeometry-hasSerialization-sub> a sh:PropertyShape ; sh:path geo:asGML ; | <S14b-many-hasSpatialAccuracy-one-sub> a sh:PropertyShape ; sh:path geo:hasSpatialAccuracy ;
- literal fork `HuygensING/shaclex:examples/shacl/qualified.ttl` — sh:PropertyShape
  - highlighted: :FemaleNodeShape sh:targetNode :carol . :FemaleShape a sh:PropertyShape ; sh:path :gender ; sh:hasValue :female ; sh:property [
- literal fork `Art-and-Rare-Materials-BF-Ext/arm:v0.1/core/validation/shacl/arm_core_property_shapes.ttl` — sh:PropertyShape
  - highlighted: :arm_endDate a sh:PropertyShape ; sh:path arm:endDate ; | :arm_marks a sh:PropertyShape ; sh:path arm:marks ;
- literal fork `AlexZouDS/gssa-vocabs:vocpub.ttl` — sh:PropertyShape
  - highlighted: <prefLabel> a sh:PropertyShape ; sh:message "Requirement 2.1.4, 2.2.1 or 2.3.1 Each vocabulary, Collection or Concept MUST have exactly one title and at least one definition indica | <definition> a sh:PropertyShape ; sh:message "Requirement 2.1.4, 2.2.1 or 2.3.1 Each vocabulary, Collection or Concept MUST have exactly one title and at least one definition indic
- literal fork `Matdata-eu/XSD2SHACL:comparison/pos.xsd.shape.ttl` — sh:PropertyShape
  - highlighted: <http://example.com/PropertyShape/Items/item/USPrice> a sh:PropertyShape ; sh:datatype xsd:decimal ; | <http://example.com/PropertyShape/Items/item/partNum> a sh:PropertyShape ; sh:datatype xsd:string ;
- literal fork `ChristianTremblay/ref-schema:model/all.ttl` — sh:PropertyShape
  - highlighted: rdfs:subClassOf ref:ExternalReference ; sh:or ( [ sh:property [ a sh:PropertyShape ; sh:datatype bacnet:Property ; | sh:path ref:read-property ], [ a sh:PropertyShape ; sh:datatype xsd:string ;
- literal fork `ckindermann/MOD:validator.ttl` — sh:PropertyShape
  - highlighted: dcatnull:resource-contactPoint a sh:PropertyShape ; sh:class vcard:Kind ; | dcatnull:resource-language a sh:PropertyShape ; sh:class dcterms:LinguisticSystem ;
- literal fork `Matdata-eu/XSD2SHACL:comparison/group.xsd.shape.ttl` — sh:PropertyShape
  - highlighted: <http://example.com/PropertyShape/DescriptionGroup/city> a sh:PropertyShape ; sh:datatype xsd:string ; | <http://example.com/PropertyShape/DescriptionGroup/name> a sh:PropertyShape ; sh:datatype xsd:string ;
- literal fork `Matdata-eu/XSD2SHACL:comparison/union.xsd.shape.ttl` — sh:PropertyShape
  - highlighted: @prefix sh: <http://www.w3.org/ns/shacl#> . @prefix xsd: <http://www.w3.org/2001/XMLSchema#> . <http://example.com/PropertyShape/partNum> a sh:PropertyShape ; sh:maxCount 1 ; sh:mi
- literal fork `TragerTech/CASE-Corpora:shapes/dct.ttl` — sh:PropertyShape
  - highlighted: sh:property [ a sh:PropertyShape ; sh:hasValue dctype:Collection ; | sh:property [ a sh:PropertyShape ; sh:nodeKind sh:BlankNodeOrIRI ;
- literal fork `Matdata-eu/XSD2SHACL:comparison/choice.xsd.shape.ttl` — sh:PropertyShape
  - highlighted: <http://example.com/PropertyShape/USAddress/city> a sh:PropertyShape ; sh:datatype xsd:string ; | <http://example.com/PropertyShape/USAddress/name> a sh:PropertyShape ; sh:datatype xsd:string ;
- literal fork `Matdata-eu/XSD2SHACL:comparison/facets.xsd.shape.ttl` — sh:PropertyShape
  - highlighted: @prefix sh: <http://www.w3.org/ns/shacl#> . @prefix xsd: <http://www.w3.org/2001/XMLSchema#> . <http://example.com/PropertyShape/partNum> a sh:PropertyShape ; sh:datatype xsd:strin
- literal fork `Matdata-eu/XSD2SHACL:comparison/union3.xsd.shape.ttl` — sh:PropertyShape
  - highlighted: @prefix sh: <http://www.w3.org/ns/shacl#> . @prefix xsd: <http://www.w3.org/2001/XMLSchema#> . <http://example.com/PropertyShape/partNum> a sh:PropertyShape ; sh:maxCount 1 ; sh:mi
- literal fork `Matdata-eu/XSD2SHACL:comparison/union2.xsd.shape.ttl` — sh:PropertyShape
  - highlighted: @prefix sh: <http://www.w3.org/ns/shacl#> . @prefix xsd: <http://www.w3.org/2001/XMLSchema#> . <http://example.com/PropertyShape/partNum> a sh:PropertyShape ; sh:maxCount 1 ; sh:mi

### code__term_target_class__ext_ttl

endpoint `code`; incomplete_results=False; ceiling_relevant=True; fetched=20.

- literal fork `netwerk-digitaal-erfgoed/lod-aggregator:shapes/shacl_edm.ttl` — sh:targetClass
  - highlighted: ex:ProvidedCHO a sh:NodeShape ; sh:targetClass edm:ProvidedCHO ; sh:property [ | ex:Aggregation a sh:NodeShape ; sh:targetClass ore:Aggregation ; sh:property[
- literal fork `HuygensING/shaclex:examples/shacl/good18.ttl` — sh:targetClass
  - highlighted: :S a sh:NodeShape; a rdfs:Class ; sh:targetNode :x; sh:targetClass :P ; sh:property [ sh:path :p; sh:datatype xsd:string;
- literal fork `HuygensING/shaclex:examples/shacl/good17.ttl` — sh:targetClass
  - highlighted: :S a sh:NodeShape ; sh:targetNode :x; sh:targetClass :P ; sh:property [ sh:path :p; sh:datatype xsd:string;
- literal fork `sepses/ics-sec-kg:src/main/resources/shacl/cat.ttl` — sh:targetClass
  - highlighted: sh:path dcterm:description ] ; sh:property [ sh:minCount 1 ; sh:path cat:accomplishesTactic ] ; sh:targetClass cat:Technique .
- literal fork `sepses/ics-sec-kg:src/main/resources/shacl/icsa.ttl` — sh:targetClass
  - highlighted: ] ; sh:property [ sh:minCount 1 ; sh:path icsa:hasProduct ; sh:dataType cpe:Product ] ; sh:targetClass icsa:ICSA .
- literal fork `sparqlunicorn/sparqlunicornGoesGIS:validation/geosparql11_validation.ttl` — sh:targetClass
  - highlighted: sh:property <S21-FeatureCollectionClass-minOneMember-feature-sub> , <S21-FeatureCollectionClass-member-onlyFeature-sub> ; sh:targetClass geo:FeatureCollection ; . | sh:property <S22-GeometryCollectionClass-minOneMember-geometry-sub> , <S22-GeometryCollectionClass-member-onlyGeometry-sub> ; sh:targetClass geo:GeometryCollection ; .
- literal fork `netwerk-digitaal-erfgoed/lod-aggregator:shapes/shacl_dataset_list_void.ttl` — sh:targetClass
  - highlighted: ex:dataset_list a sh:NodeShape ; # focus on the resources from the schema:Dataset class sh:targetClass void:Dataset; # a title is required sh:property [
- literal fork `netwerk-digitaal-erfgoed/lod-aggregator:shapes/shacl_dataset_dump_dcat.ttl` — sh:targetClass
  - highlighted: # focus on the resources from the dcat:Dataset class sh:targetClass dcat:Dataset; | # focus on the resources from the dcat:Distribution class sh:targetClass dcat:Distribution ;
- literal fork `netwerk-digitaal-erfgoed/lod-aggregator:shapes/shacl_dataset_list_dcat.ttl` — sh:targetClass
  - highlighted: ex:dataset_list a sh:NodeShape ; # focus on the resources from the schema:Dataset class sh:targetClass dcat:Dataset; # a title is required sh:property [
- literal fork `netwerk-digitaal-erfgoed/lod-aggregator:shapes/shacl_dataset_dump_schema.ttl` — sh:targetClass
  - highlighted: # focus on the resources from the schema:Dataset class sh:targetClass schema:Dataset; | # focus on the resources from the dcat:Distribution class sh:targetClass schema:DataDownload ;
- literal fork `netwerk-digitaal-erfgoed/lod-aggregator:shapes/shacl_dataset_list_schema.ttl` — sh:targetClass
  - highlighted: ex:dataset_list a sh:NodeShape ; # focus on the resources from the schema:Dataset class sh:targetClass schema:Dataset; # a title is required sh:property [
- literal fork `Orange-OpenSource/pygraft-gen:evaluation/resilience/uc_shacl.ttl` — sh:targetClass
  - highlighted: ex:ResilienceShape # The 'k out-of n' resilience issue a sh:NodeShape ; sh:targetClass noria:Application ; # Looking for Applications sh:property [ # Looking for an alarm at the Ap
- literal fork `sepses/ics-sec-kg:src/main/resources/shacl/cve.ttl` — sh:targetClass
  - highlighted: ] ; sh:property [ sh:minCount 0 ; sh:path cve:hasVulnerableConfiguration ; sh:dataType cve:LogicalTest ] ; sh:targetClass cve:CVE .
- literal fork `HuygensING/shaclex:examples/shacl/report/issueShapes.ttl` — sh:targetClass
  - highlighted: ex:IssueShape a sh:NodeShape ; sh:targetClass ex:Issue; sh:property [ sh:path ex:state ; sh:in (ex:unassigned ex:assigned) ;
- literal fork `PaulWang1905/ontology:shacl.ttl` — sh:targetClass
  - highlighted: :CertificationShape a sh:NodeShape; sh:targetClass :Certification; sh:property :labelShape; | :LicenseShape a sh:NodeShape; sh:targetClass :License; sh:property :labelShape,

### code__broad_shacl

endpoint `code`; incomplete_results=False; ceiling_relevant=True; fetched=20.

- literal fork `antoine2711/artsdata-data-model:shacl_reports.md` — base.html %} {% include last-modified.html %} ## SHACL Reports [Edit page](https://github.com/culturecre
  - highlighted: ## SHACL Reports [Edit page](https://github.com/culturecreates/artsdata-data-model/blob/master/{{page.path}}) | <span id="last-modified"></span> | The Artsdata.ca Databus uses SHACL shapes to validate input data. A report is generated with each call to the Databus. The SHACL report is a summary of data graph nodes in violatio
- literal fork `SolidOS/userguide:README.md` — e a text files (e.g., Turtle, JSON, RDF, ShEx and SHACL shapes, etc.). 4. Select the type of resource you
  - highlighted: * <img src="https://solidos.github.io/solid-ui/src/icons/noun_66617.svg" alt="Meeting" width="16" > [Meeting](./views/meeting/userguide.md). * <img src="https://solidos.github.io/s
- literal fork `christian-edelsbrunner/pycgmes:shacl/build.md` — he-2.0 --> # Why this directory It contains the SHACL build files, only meant to build a second distrib
  - highlighted: It contains the SHACL build files, only meant to build a second distribution package. The CI & co happen in the main poetry/github files. | The main `pycgmes` package does not have the SHACL files.
- literal fork `MuazzamChaud/csvcubed:shacl/README.md` — # SHACL Shapes **N.B. SHACL Shapes are a work-in-progres
  - highlighted: # SHACL Shapes **N.B. SHACL Shapes are a work-in-progress.** This directory contains a versioned history of the RDF shape of csvcubed's outputs. The purpose of these SHACL shape de
- literal fork `linkeddata/rabel:README.md` — in the test manifest -validate=shapeFile Run a SHACL validator on the data loaded by previous in=x -ve
  - highlighted: -size Give the current store -spray=base Write out linked data to lots of different linked files CAREFUL! -test=manifest Run tests as described in the test manifest -validate=shape
- literal fork `dice-group/deer:docs/README.md` — tend Generation enabled through extensive use of [SHACL](https://www.w3.org/TR/shacl/) ## Getting Starte
  - highlighted: - Built for professionals (cli, Web service) and lay users (Web frontend) - Embeddable in your own project - Extensible by design (plugin system with [PF4J](https://pf4j.org)) - Va
- literal fork `Art-and-Rare-Materials-BF-Ext/arm:v0.1/readme.md` — on profiles](application_profiles), formalized in SHACL and accompanied by external ontologies and vocabu
  - highlighted: In addition to the ontologies, the group has generated several other outputs: - [A set of controlled vocabularies](core/vocabularies/) for arrangement of physical objects (e.g., ro
- literal fork `bci-oss/esmf-semantic-aspect-meta-model:README.md` — odule, as well the formal specification parts as [SHACL](https://www.w3.org/TR/shacl/) shapes. The sourc
  - highlighted: This repository contains the detailed documentation of the SAMM specification as an [Antora](https://antora.org/) module, as well the formal specification parts as [SHACL](https://
- literal fork `WileyLabs/shacl:README.md` — # TopBraid SHACL API **An open source implementation of the W3C
  - highlighted: Can be used to perform SHACL constraint checking and rule inferencing in any Jena-based Java application. This API also serves as a reference implementation of the SHACL spec. | https://groups.google.com/forum/#!forum/topbraid-users Please prefix your messages with [SHACL API]
- literal fork `iop-alliance/OpenKnowHow:README.md` — o humans ([Markdown], HTML, PDF) or one program ([SHACL] (tbd)) or the other ([JSON-Schema] (tbd)). This
  - highlighted: tailored either to humans ([Markdown], HTML, PDF) or one program ([SHACL] (tbd)) or the other ([JSON-Schema] (tbd)). | https://github.com/OPEN-NEXT/LOSH-OKH-tool#validation). Once our [SHACL] generation works well though, we will be able to use "off the shelf" [SHACL] validators instead,
- literal fork `WileyLabs/shacl:process.md` — he Project This page describes processes for the SHACL API Project. ---- ## Local Build To build the
  - highlighted: This page describes processes for the SHACL API Project. | ``` git clone https://github.com/TopQuadrant/shacl cd shacl
- literal fork `Informatievlaanderen/OSLO-Validator:README.md` — tor is beschikbaar via https://data.vlaanderen.be/shacl-validator/ of kan lokaal geïnstalleerd worden met
  - highlighted: Deze repository bevat de source code voor een tool die toelaat om data te valideren tegen de [OSLO applicatieprofielen](https://data.vlaanderen.be/ns#Applicatieprofielen). Deze val | This tool provides a way of validating RDF graphs against the [Application Profiles available within the OSLO² context](http://data.vlaanderen.be/ns/#Applicatieprofielen). The vali
- literal fork `sepses/ics-sec-kg:README.md` — 283-01</a>. </li> </ol> ## RML Mapping & SHACL Validation To guarantee the quality and consisten
  - highlighted: </ol> ## RML Mapping & SHACL Validation To guarantee the quality and consistency of the constructed knowledge graph, ICS-SEC leveraged a declarative RDF Mapping (i.e., RML) and use
- literal fork `industrial-data-space/InformationModel:NOTES.md` — be#h3_wf-rules), validating resource (SPARQL ASK, SHACL etc.) and prose description
  - highlighted: - What are the entities to be permanently and uniformally identified, e.g. their PID must be immutable and constant across catalogs? Examples: Participant, Connector. ## TODOs - in
- literal fork `HuygensING/shaclex:README.md` — # shaclex SHACL and SHEX Implementation. This project c
  - highlighted: SHACL and SHEX Implementation. | This project contains an implementation of [SHACL](http://w3c.github.io/data-shapes/shacl/) and [ShEx](http://www.shex.io)

### repository__topic_shacl

endpoint `repository`; incomplete_results=False; ceiling_relevant=False; fetched=20.

- literal `neo4j-labs/neosemantics` — topic list contains shacl
- literal `fabio-rovai/open-ontologies` — topic list contains shacl
- literal `DerwenAI/kglab` — topic list contains shacl
- literal `linkml/linkml` — topic list contains shacl
- literal `eclipse-rdf4j/rdf4j` — topic list contains shacl
- literal `databrickslabs/ontobricks` — topic list contains shacl
- literal `RDFLib/pySHACL` — topic list contains shacl
- literal `sparna-git/Sparnatural` — topic list contains shacl
- literal `BlueBrain/nexus` — topic list contains shacl
- literal `TopQuadrant/shacl` — topic list contains shacl
- literal `AKSW/RDFUnit` — topic list contains shacl
- literal `google/schemarama` — topic list contains shacl
- literal `mdesalvo/RDFSharp` — topic list contains shacl
- literal `zazuko/rdf-validate-shacl` — topic list contains shacl
- literal `Wimmics/corese` — topic list contains shacl

### repository__broad_shacl

endpoint `repository`; incomplete_results=False; ceiling_relevant=True; fetched=20.

- literal `TopQuadrant/shacl` — TopQuadrant/shacl SHACL API in Java based on Apache Jena shacl # To
  - highlighted: TopQuadrant/shacl SHACL API in Java based on Apache Jena shacl # To
- literal `RDFLib/pySHACL` — RDFLib/pySHACL A Python validator for SHACL constraints owl rdf
  - highlighted: RDFLib/pySHACL A Python validator for SHACL constraints owl rdf
- literal `jbarrasa/goingmeta` — Apr 5 | Controlling the shape of your graph with SHACL |`data quality` `SHACL` `n10s`| [📺](https://youtu
  - highlighted: Apr 5 | Controlling the shape of your graph with SHACL |`data quality` `SHACL` `n10s`| [📺](https://youtu
- literal `w3c/data-shapes` — The WG is currently working on updated and new [SHACL](https://www.w3.org/TR/shacl/) recommendations, a
  - highlighted: The WG is currently working on updated and new [SHACL](https://www.w3.org/TR/shacl/) recommendations, a
- literal `qudt/qudt-public-repo` — o/releases) and load one of: - QUDT-all-in-one-SHACL.ttl - QUDT-all-in-one-OWL.ttl dependi
  - highlighted: o/releases) and load one of: - QUDT-all-in-one-SHACL.ttl - QUDT-all-in-one-OWL.ttl dependi
- literal `open-metadata/OpenMetadata` — ROD, PROV-O, OpenLineage, ODCS, RDF/OWL, JSON-LD, SHACL, JSON Schema, APIs, events, and metadata schemas
  - highlighted: ROD, PROV-O, OpenLineage, ODCS, RDF/OWL, JSON-LD, SHACL, JSON Schema, APIs, events, and metadata schemas
- literal `semantalytics/awesome-semantic-web` — linked-data) - [CSVW](#csvw) - [WebID](#webid) - [SHACL Implementations](#shacl-implementations) - [SKOS
  - highlighted: linked-data) - [CSVW](#csvw) - [WebID](#webid) - [SHACL Implementations](#shacl-implementations) - [SKOS
- literal `sparna-git/Sparnatural` — er with SPARQL, in the browser, configurable with SHACL knowledge-graph linked-data owl rdf shacl sparnat
  - highlighted: er with SPARQL, in the browser, configurable with SHACL knowledge-graph linked-data owl rdf shacl sparnat
- literal `AKSW/RDFUnit` — ecks data-validation rdf schema schema-validation shacl unit-testing validation web-ontology-language RDF
  - highlighted: ecks data-validation rdf schema schema-validation shacl unit-testing validation web-ontology-language RDF
- literal `semantica-agi/semantica` — ure. Ontologies and controlled vocabularies (OWL, SHACL, SKOS) make what an entity *means* to your busine
  - highlighted: ure. Ontologies and controlled vocabularies (OWL, SHACL, SKOS) make what an entity *means* to your busine
- literal `w3c/shacl` — w3c/shacl SHACL Community Group (Post-REC activitities) #
  - highlighted: w3c/shacl SHACL Community Group (Post-REC activitities) #
- literal `ULB-Darmstadt/shacl-form` — ULB-Darmstadt/shacl-form HTML5 web component to edit, view and query
  - highlighted: ULB-Darmstadt/shacl-form HTML5 web component to edit, view and query
- literal `sparna-git/shacl-play` — sparna-git/shacl-play SHACL validation UI, SHACL documentation gen
  - highlighted: sparna-git/shacl-play SHACL validation UI, SHACL documentation gen
- literal `cloudbadal007/foundry-ontology-open` — Palantir Foundry's Ontology architecture with OWL/SHACL export bridge # Foundry Ontology Open **Open-so
  - highlighted: Palantir Foundry's Ontology architecture with OWL/SHACL export bridge # Foundry Ontology Open **Open-so
- literal `weso/shaclex` — weso/shaclex SHACL/ShEx implementation earl-report rdf-libr
  - highlighted: weso/shaclex SHACL/ShEx implementation earl-report rdf-libr

No discovery query was changed.

## Follow-up: `fork:true` on code search

The seven planned code queries all send `fork:true`. Their first 20 hits were forks. A separate check of `"sh:NodeShape" in:file extension:ttl` compared three qualifier forms. Page size is noted below. This check is not one of the seven planned queries, and it did not change the configuration.

| query | reported_total | what the fetched page contained |
| --- | ---: | --- |
| `"sh:NodeShape" in:file extension:ttl` | 31168 | page 1, 5 hits, 0 forks |
| `"sh:NodeShape" in:file extension:ttl fork:true` | 10688 | page 10, 100 hits, 100 forks |
| `"sh:NodeShape" in:file extension:ttl fork:only` | 10688 | page 1, 5 hits, 5 forks; same leading repositories as `fork:true` |

On this code query, `fork:true` and `fork:only` reported the same total. The query with no fork qualifier reported a larger total and its first hits were not forks. The first 1000 `fork:true` hits are not a sample of non-fork repositories: hits 901–1000 were still forks.

`topic:shacl is:public fork:only` reported 3 repositories, and all 3 fetched items were forks. The first 20 hits of `topic:shacl is:public fork:true` were not forks. Repository search therefore does not show the same `fork:true` behavior as this code query.
