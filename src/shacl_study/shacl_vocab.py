"""Evidence categories derived from the W3C SHACL namespace document.

The vendored file is https://www.w3.org/ns/shacl.ttl. Predicate sets are read
from that graph. This module does not treat a hand-written predicate list as
the definition of SHACL Core, and it does not call SHACL-SPARQL terms Core.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS

SH = "http://www.w3.org/ns/shacl#"
SOURCE_URL = "https://www.w3.org/ns/shacl.ttl"
VOCAB_PATH = Path(__file__).resolve().parent / "data" / "w3c-shacl.ttl"

NODE_SHAPE = SH + "NodeShape"
PROPERTY_SHAPE = SH + "PropertyShape"
SHAPE = SH + "Shape"
PROPERTY_SHAPE_CLASS = SH + "PropertyShape"
CONSTRAINT_COMPONENT = SH + "ConstraintComponent"
PARAMETER = SH + "Parameter"
PATH_PREDICATE = SH + "path"
SPARQL_EXECUTABLE = SH + "SPARQLExecutable"
RDF_TYPE = str(RDF.type)

# Query-body properties. Prefix machinery such as sh:prefixes is recorded
# separately and does not by itself verify a repository.
_SPARQL_QUERY_CLASSES = {
    SH + "SPARQLAskExecutable",
    SH + "SPARQLSelectExecutable",
    SH + "SPARQLConstructExecutable",
    SH + "SPARQLUpdateExecutable",
}


@dataclass(frozen=True)
class ShaclVocabulary:
    source_url: str
    path: str
    sha256: str
    core_constraint_parameters: frozenset[str]
    core_target_predicates: frozenset[str]
    core_path_predicates: frozenset[str]
    sparql_evidence_predicates: frozenset[str]
    excluded_components: frozenset[str]

    @property
    def core_predicates(self) -> frozenset[str]:
        return self.core_constraint_parameters | self.core_target_predicates | self.core_path_predicates

    def as_report(self) -> dict:
        return {
            "source_url": self.source_url,
            "path": self.path,
            "sha256": self.sha256,
            "core_constraint_parameters": _locals(self.core_constraint_parameters),
            "core_target_predicates": _locals(self.core_target_predicates),
            "core_path_predicates": _locals(self.core_path_predicates),
            "sparql_evidence_predicates": _locals(self.sparql_evidence_predicates),
            "excluded_components": _locals(self.excluded_components),
            "derivation": (
                "Core constraint parameters are sh:path values of sh:Parameter nodes "
                "on sh:ConstraintComponent instances whose rdfs:label does not identify "
                "a SPARQL, JavaScript, or expression component. "
                "Core targets are rdf:Property values with rdfs:domain sh:Shape whose "
                "local name starts with 'target'. "
                "sh:path is included when the vocabulary gives it rdfs:domain sh:PropertyShape. "
                "SHACL-SPARQL evidence predicates are sh:sparql plus properties whose "
                "rdfs:domain is a SPARQL ASK, SELECT, CONSTRUCT, or UPDATE executable. "
                "sh:sparql, sh:select, and sh:ask are not SHACL Core constraints."
            ),
        }


def load_vocabulary(path: Path | None = None) -> ShaclVocabulary:
    vocab_path = path or VOCAB_PATH
    raw = vocab_path.read_bytes()
    graph = Graph()
    graph.parse(data=raw.decode("utf-8"), format="turtle")
    excluded = _excluded_components(graph)
    return ShaclVocabulary(
        source_url=SOURCE_URL,
        path=str(vocab_path),
        sha256=hashlib.sha256(raw).hexdigest(),
        core_constraint_parameters=frozenset(_core_constraint_parameters(graph, excluded)),
        core_target_predicates=frozenset(_core_targets(graph)),
        core_path_predicates=frozenset(_property_shape_path(graph)),
        sparql_evidence_predicates=frozenset(_sparql_evidence_predicates(graph, excluded)),
        excluded_components=frozenset(excluded),
    )


@lru_cache(maxsize=1)
def default_vocabulary() -> ShaclVocabulary:
    return load_vocabulary()


def _excluded_components(graph: Graph) -> set[str]:
    excluded: set[str] = set()
    for component in graph.subjects(RDF.type, URIRef(CONSTRAINT_COMPONENT)):
        label = str(graph.value(component, RDFS.label) or "").lower()
        if any(token in label for token in ("sparql", "javascript", "expression")):
            excluded.add(str(component))
    return excluded


def _core_constraint_parameters(graph: Graph, excluded: set[str]) -> set[str]:
    paths: set[str] = set()
    for component in graph.subjects(RDF.type, URIRef(CONSTRAINT_COMPONENT)):
        if str(component) in excluded:
            continue
        for parameter in graph.objects(component, URIRef(SH + "parameter")):
            path = graph.value(parameter, URIRef(PATH_PREDICATE))
            if isinstance(path, URIRef) and str(path).startswith(SH):
                paths.add(str(path))
    return paths


def _core_targets(graph: Graph) -> set[str]:
    targets: set[str] = set()
    for prop in graph.subjects(RDF.type, RDF.Property):
        iri = str(prop)
        if not iri.startswith(SH):
            continue
        if graph.value(prop, RDFS.domain) != URIRef(SHAPE):
            continue
        if iri.rsplit("#", 1)[-1].startswith("target"):
            targets.add(iri)
    return targets


def _property_shape_path(graph: Graph) -> set[str]:
    prop = URIRef(PATH_PREDICATE)
    if (prop, RDF.type, RDF.Property) in graph and (prop, RDFS.domain, URIRef(PROPERTY_SHAPE_CLASS)) in graph:
        return {PATH_PREDICATE}
    return set()


def _sparql_evidence_predicates(graph: Graph, excluded: set[str]) -> set[str]:
    predicates: set[str] = set()
    for component in excluded:
        if "SPARQLConstraintComponent" not in component:
            continue
        for parameter in graph.objects(URIRef(component), URIRef(SH + "parameter")):
            path = graph.value(parameter, URIRef(PATH_PREDICATE))
            if isinstance(path, URIRef):
                predicates.add(str(path))
    for prop in graph.subjects(RDF.type, RDF.Property):
        domain = graph.value(prop, RDFS.domain)
        if domain is not None and str(domain) in _SPARQL_QUERY_CLASSES:
            predicates.add(str(prop))
    return predicates


def _locals(iris: frozenset[str]) -> list[str]:
    return sorted(iri.rsplit("#", 1)[-1] for iri in iris)


def prefilter_needles(vocab: ShaclVocabulary) -> tuple[str, ...]:
    """Byte strings that justify parsing. A miss does not prove absence."""
    needles = {SH, "sh:NodeShape", "sh:PropertyShape"}
    for iri in vocab.core_predicates | vocab.sparql_evidence_predicates:
        local = iri.rsplit("#", 1)[-1]
        needles.add(f"sh:{local}")
        needles.add(iri)
    return tuple(sorted(needles))
