# Interfaces and evidence contract

## CLI

Global `--db PATH` selects a local database. `--jac-command JSON_ARRAY` selects
the trusted compiler executable and optional launcher arguments. Defaults to
`["jac"]`; the environment variable `JACBRAIN_JAC_COMMAND` overrides it.

* `ingest PATH --project ID --jac-version VERSION`: Document and lexical Symbols.
* `remember PATH --kind KIND --project ID --jac-version VERSION`: explicit
  Concept, Diagnostic, Fix, Pattern, Task or other evidence. All start as candidates.
* `link SOURCE RELATION TARGET`: scoped, idempotent graph relation.
* `context TASK --project ID --jac-version VERSION --max-bytes 6000`: compact JSON.
* `validate ID`: run official Jac MCP against stored candidate source.
* `mcp`: JSON-RPC 2.0 / MCP 2024-11-05 over newline-delimited stdio.

CLI exit 0 means success, 1 means compiler rejection, 2 means input/tooling error.
No tool lets an agent submit a claimed validation receipt or choose a shell
command. The internal Store API is trusted library code, not an authenticity
boundary against a local process that can edit the SQLite database.

## Context packet

`schema_version`, `trust`, `items`, `truncated`, `budget_unit`. Every item has
ID, kind, content, source URI, content hash, status and Jac version. The bound
applies to the UTF-8 bytes of `json.dumps(packet, ensure_ascii=False)`, excluding
transport framing and the CLI newline. It is a conservative size control,
not a tokenizer-based count. Records that do not fit use a bounded matching
excerpt with character offsets and `is_excerpt: true`. The hash/status still
describe the complete stored source. Metadata alone may exceed a tiny budget,
in which case the item is omitted and `truncated` is true.

Exact project and compiler version are required. No implicit fallback to older
evidence. Related records may be included even if they have no lexical match.
Version labels on ingested docs are caller-provided provenance, not proof that
the documentation is correct for that version.

## Validation

Candidate status is `candidate` or `compiler_validated`; replaced source is
`superseded` and excluded from default retrieval. Re-ingestion retires previous
records at the same source/kind/version and the file's lexical symbols. Files
deleted outside JacBrain are not detected automatically. A trusted adapter
reads installed Jac version, discovers `validate_jac`, calls it with the exact
stored content, and persists the returned payload plus SHA-256 digest. Changed
content receives a different ID. Rejection clears previous compiler-valid status.
Successful compilation says nothing about a fix reproducing/resolving a bug.
Full before/after project snapshots and behavioral evidence are roadmap work.

Use only trusted source and dependencies. Compilation can process imports and
compile-time operations. A subprocess timeout is a resource bound, not a
security sandbox. POSIX cleanup targets the process group; Windows wrapper
descendants may outlive the request, although stream cleanup is bounded. Run
directly under Linux/WSL for stricter process cleanup. This local single-user
MVP is unsuitable as a public API.
