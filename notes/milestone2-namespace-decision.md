# Canonical SHACL namespace

`verified_shacl` uses only the canonical namespace `http://www.w3.org/ns/shacl#`.

`https://www.w3.org/ns/shacl#` is a different IRI. Source RDF is not rewritten to turn one into the other.

A repository whose shape structures use only the https IRI is recorded as `noncanonical_shacl_namespace`. That status is not part of the canonical verified corpus. The file path, the exact namespace, and the local terms (`NodeShape`, `PropertyShape`, `path`, `targetClass`, and the other derived shape predicates) are kept.

If a repository also has canonical http shape evidence, its status stays `verified_shacl` and `noncanonical_shacl_namespace_detected` is true.
