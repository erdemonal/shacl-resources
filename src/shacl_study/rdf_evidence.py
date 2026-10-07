"""Classify parsed RDF triples into SHACL evidence categories."""

from __future__ import annotations

from dataclasses import dataclass, field

from rdflib import BNode, Graph, Literal, URIRef

from shacl_study.shacl_vocab import NODE_SHAPE, PROPERTY_SHAPE, RDF_TYPE, SH, ShaclVocabulary

SHACL_NAMESPACE_IRIS = (SH, "http://www.w3.org/ns/shacl")
HTTPS_SHACL = "https://www.w3.org/ns/shacl#"
_QUERY_LOCALS = frozenset({"select", "ask", "construct", "update"})


@dataclass
class GraphEvidence:
    core_triples: int = 0
    sparql_triples: int = 0
    other_triples: int = 0
    node_shape_subjects: set[str] = field(default_factory=set)
    property_shape_subjects: set[str] = field(default_factory=set)
    evidence: set[str] = field(default_factory=set)
    noncanonical_detected: bool = False
    noncanonical_namespaces: set[str] = field(default_factory=set)
    noncanonical_shape_terms: set[str] = field(default_factory=set)

    @property
    def verifies(self) -> bool:
        return self.core_triples > 0 or self.sparql_triples > 0


def parse_rdf(payload: bytes, parser_format: str) -> Graph:
    graph = Graph()
    graph.parse(data=payload, format=parser_format)
    return graph


def classify_graph(graph: Graph, vocab: ShaclVocabulary) -> GraphEvidence:
    triples = list(graph)
    linked_constraints = set()
    typed_constraints = set()
    query_subjects = set()
    for subject, predicate, obj in triples:
        predicate_iri = str(predicate)
        if _local_name(predicate_iri) == "sparql" and _is_shacl_iri(predicate_iri):
            linked_constraints.add(obj)
        if predicate_iri == RDF_TYPE and _is_sparql_type(obj, vocab):
            typed_constraints.add(subject)
        if _local_name(predicate_iri) in _QUERY_LOCALS and _is_shacl_iri(predicate_iri):
            query_subjects.add(subject)
    evidence = GraphEvidence()
    for subject, predicate, obj in triples:
        predicate_iri = str(predicate)
        object_iri = str(obj) if isinstance(obj, URIRef) else ""
        kind = _triple_kind(predicate_iri, object_iri, vocab)
        structural = _sparql_structure(
            subject,
            predicate_iri,
            obj,
            kind,
            linked_constraints=linked_constraints,
            typed_constraints=typed_constraints,
            query_subjects=query_subjects,
        )
        if kind == "core_type_node":
            evidence.core_triples += 1
            evidence.node_shape_subjects.add(_subject_key(subject))
            evidence.evidence.add("rdf:type sh:NodeShape")
        elif kind == "core_type_property":
            evidence.core_triples += 1
            evidence.property_shape_subjects.add(_subject_key(subject))
            evidence.evidence.add("rdf:type sh:PropertyShape")
        elif kind == "core":
            evidence.core_triples += 1
            evidence.evidence.add(_curie(predicate_iri))
        elif kind == "sparql" and structural:
            evidence.sparql_triples += 1
            evidence.evidence.add(_curie(predicate_iri))
        elif _mentions_shacl(subject, predicate, obj):
            evidence.other_triples += 1
        _record_https(evidence, subject, predicate_iri, object_iri, vocab, structural=structural)
    return evidence


def _sparql_structure(
    subject,
    predicate_iri: str,
    obj,
    kind: str,
    *,
    linked_constraints: set,
    typed_constraints: set,
    query_subjects: set,
) -> bool:
    """Query-body predicates verify only inside a SHACL-SPARQL structure."""
    if kind != "sparql":
        return False
    local = _local_name(predicate_iri)
    if local in _QUERY_LOCALS:
        return subject in linked_constraints or subject in typed_constraints
    if local == "sparql":
        return obj in query_subjects or obj in typed_constraints
    return subject in linked_constraints or subject in typed_constraints


def _is_sparql_type(obj, vocab: ShaclVocabulary) -> bool:
    if not isinstance(obj, URIRef):
        return False
    iri = str(obj)
    if iri in vocab.sparql_constraint_types:
        return True
    if iri.startswith(HTTPS_SHACL):
        return (SH + iri[len(HTTPS_SHACL) :]) in vocab.sparql_constraint_types
    return False


def _is_shacl_iri(iri: str) -> bool:
    return iri.startswith(SH) or iri.startswith(HTTPS_SHACL)


def _local_name(iri: str) -> str:
    if iri.startswith(HTTPS_SHACL):
        return iri[len(HTTPS_SHACL) :]
    if iri.startswith(SH):
        return iri[len(SH) :]
    return iri.rsplit("#", 1)[-1]


def _triple_kind(predicate_iri: str, object_iri: str, vocab: ShaclVocabulary) -> str:
    if predicate_iri == RDF_TYPE and object_iri == NODE_SHAPE:
        return "core_type_node"
    if predicate_iri == RDF_TYPE and object_iri == PROPERTY_SHAPE:
        return "core_type_property"
    if predicate_iri in vocab.core_predicates:
        return "core"
    if predicate_iri in vocab.sparql_evidence_predicates:
        return "sparql"
    return ""


def _record_https(
    evidence: GraphEvidence,
    subject,
    predicate_iri: str,
    object_iri: str,
    vocab: ShaclVocabulary,
    *,
    structural: bool,
) -> None:
    """Record https namespace IRIs without rewriting them into the http namespace."""
    iris = []
    if isinstance(subject, URIRef):
        iris.append(str(subject))
    iris.extend([predicate_iri, object_iri])
    if any(iri.startswith(HTTPS_SHACL) for iri in iris):
        evidence.noncanonical_detected = True
        evidence.noncanonical_namespaces.add(HTTPS_SHACL)
    if predicate_iri == RDF_TYPE and object_iri.startswith(HTTPS_SHACL):
        local = object_iri[len(HTTPS_SHACL) :]
        if local in {"NodeShape", "PropertyShape"}:
            evidence.noncanonical_shape_terms.add(local)
    if predicate_iri.startswith(HTTPS_SHACL):
        local = predicate_iri[len(HTTPS_SHACL) :]
        core_locals = {iri.rsplit("#", 1)[-1] for iri in vocab.core_predicates}
        if local in core_locals or (structural and local in _shape_locals(vocab)):
            evidence.noncanonical_shape_terms.add(local)


def _shape_locals(vocab: ShaclVocabulary) -> set[str]:
    iris = vocab.core_predicates | vocab.sparql_evidence_predicates
    return {iri.rsplit("#", 1)[-1] for iri in iris}


def _mentions_shacl(subject, predicate, obj) -> bool:
    return any(_in_namespace(term) for term in (subject, predicate, obj))


def _in_namespace(term) -> bool:
    if isinstance(term, Literal) or isinstance(term, BNode):
        return False
    iri = str(term)
    return iri.startswith(SHACL_NAMESPACE_IRIS[0]) or iri.rstrip("/") == SHACL_NAMESPACE_IRIS[1]


def _subject_key(subject) -> str:
    if isinstance(subject, BNode):
        return f"bnode:{subject}"
    return str(subject)


def _curie(iri: str) -> str:
    if iri.startswith(SH):
        return "sh:" + iri[len(SH) :]
    return iri
