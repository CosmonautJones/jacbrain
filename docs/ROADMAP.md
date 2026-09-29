# Roadmap with acceptance gates

## M0: Inspectable foundation (this release)

Explicit file ingestion; immutable versioned records; typed links; bounded
context; real snippet validation through Jac MCP; separate executable Jac
graph model; Windows/Linux tests; documented prior art and limitations.
Acceptance: automated core tests and actual valid/invalid Jac MCP cases pass.

## M1: Compiler-backed project context

Replace lexical Symbol candidates with `jac code map/symbol/uses/slice/diag`.
Record source-tree digest (including dirty files), compiler binary hash,
dependency snapshot and doc resource hashes. Persist/import the same evidence
contract in the native Jac graph. Acceptance: project imports, implementation
splits and changed files invalidate evidence correctly; no competing truth stores.

## M2: Reproducible repair episodes

Record failing reproduction, before/after source, compiler/project test commands,
results and runtime checks. Promote only a fix verified for that environment;
mark changed dependencies stale. Acceptance: deliberately bad fixes and forged
receipts cannot become verified, while a replayable known fix does.

## M3: Measured context efficiency

Freeze a held-out Jac task set and compare official Jac MCP + code slice,
flat searchable notes, and graph retrieval. Measure actual tokenizer counts,
all tool-output tokens, task success, repair rounds and latency. Acceptance:
publish raw reproducible measurements, including failures and costs. Keep a
graph only where it beats simpler search on useful outcomes.

## M4: Operational hardening

Incremental ingestion, source deletion/supersession, migrations, bounded large
corpora, stable MCP conformance tests, multi-user isolation only if needed.
Acceptance: resumable interrupted indexing, backup/restore and dependency
drift tests. No hosted service or autonomous source execution before isolation.
