# Jac documentation memory and measured context

User approved building the documentation knowledge base and measuring whether
it helps us build Jac with fewer tokens and mistakes. Execute within existing
accounts, no new paid service or hosting purchase.

## Design

Import versioned guides from the installed Jac MCP resources. Preserve complete
source hashes and section boundaries; link explicit guide references. Keep that
shared language corpus separate from private project records, but query both
at the exact requested Jac version. Rank sections rather than entire manuals,
with bounded graph expansion and a hard output budget.

The experiment must separate context compression from coding effectiveness.
Compare a full-guide baseline, official MCP search_docs, lexical chunks and
graph context with the same frozen task prompts. Count actual tokens with a
named tokenizer. Run a small paired model pilot if the existing authenticated
coding tool is available; compile and behavior-test every produced answer.
Report all failures and whole-run usage, including overhead and cached tokens.
Do not infer fewer mistakes or better coding from shorter context alone.

## Tasks and ownership

- [x] Corpus ingestion: MCP resource discovery, section chunks, provenance,
  explicit dependency edges, atomic refresh and supersession tests.
- [x] Retrieval: rare-term ranking, shared-corpus/version isolation,
  bounded dependency expansion, excerpts and byte-budget regressions.
- [x] Interface: CLI sync-guides and agent context support; runnable guide.
- [x] Evaluation: freeze four tasks before retrieval tuning; actual token counts,
  baseline outputs and real Jac checks. Label this as a small pilot, not proof.
- [ ] Delivery: independent review, targeted tests, exact-head CI, PR and report.

Independent ingestion, frozen task design, and the previously authorized
M-Local hosting work are delegated. Retrieval and the benchmark runner are
implemented here. Preserve all unrelated user work.
