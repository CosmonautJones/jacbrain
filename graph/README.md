# Native Jac graph boundary

This is a Jac 0.37.23 language scaffold with real typed nodes, typed edges and
traversing walkers. The Python service currently owns the separate SQLite
reference projection. No synchronization, persistence adapter or production Jac
service is implemented here.

`Evidence` carries an explicit kind: Concept, Document, Symbol, Diagnostic, Fix,
Pattern, Task or Validation. All records retain evidence ID, source URI,
SHA-256 source hash, Jac version and project identity. `Contains` links a
KnowledgeGraph to its records; `Relation` identifies engineering relationships.
The record identity is `(project_id, jac_version, evidence_id)`.

- `UpsertEvidence` preserves identity and clears promotion when source/content
  changes. Updating Validation evidence conservatively revokes linked promotions.
- `LinkEvidence` requires both endpoints in the requested project and version,
  deduplicates the same relation and permits only Validation records to validate.
- `TaskContext` follows outgoing relationships breadth first, with cycle
  suppression, version/project barriers, at most 100 results and five hops.
  Its default is 20 results and two hops. Budgets bound returned/visited nodes;
  this in-memory scaffold still reads adjacency lists and scans its catalog.
- `PromoteEvidence` recalculates promotion from an incoming `validates` edge,
  passing status and exact source hash, project and toolchain match.

These walkers are private in-process operations. They accept trusted caller
records; the scaffold does not authenticate compiler proofs. Callers must not
turn arbitrary user-supplied `passed` text into trusted validation. Direct field
mutation bypasses upsert invalidation, so recalculate promotion before use.
Compiler execution and provenance ingestion live in the Python layer.

The demo is explicitly synthetic and makes no recorded validation claim.
It uses a transient KnowledgeGraph without attaching anything to `root`.
Tests create fresh transient graphs independently. Runtime compilation may write
local `.jac` artifacts, but application nodes are not persisted.

From the repository directory in WSL Bash:

```bash
jac --version                 # must be 0.37.23
jac check main.jac graph tests/graph_tests.jac
jac test tests/graph_tests.jac -v
jac run main.jac
```

The repository-level Python README describes installation and the separately
verified persistence/ingestion/MCP prototype. This module does not serve an API.
