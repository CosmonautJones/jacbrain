# JacBrain prior art and implementable integration

Research checked 2026-09-29. Primary-source inspection, not runtime validation. Recommendation: build a thin, version-aware context and repair-evidence layer over Jac's existing compiler tools. Do not build a replacement compiler graph or another general coding agent.

## Most important finding: Jac already supplies much of the proposed base

The GitHub latest-release API returned **v0.37.23**, published September 24, 2026. Its annotated tag resolves to commit `58cb97eb75cdff8b5ee78f4094ca2be16376601c`. Release assets listed Linux x86_64/aarch64 and macOS aarch64 binaries, with hashes, but no Windows binary. Use the existing pinned WSL installation for the first implementation, and verify its actual version/hash. PyPI's `jaclang/0.37.23` endpoint returned 404; do not assume `pip install jaclang==0.37.23` is the installation path. Main and other version tags can diverge from the published release. [Release](https://github.com/jaseci-labs/jac/releases/tag/v0.37.23), [release API](https://api.github.com/repos/jaseci-labs/jac/releases/latest).

Pinned source includes compiler-backed structural queries with JSON output (`schema_version: 1`):

```text
jac code symbol User
jac code uses make_user
jac code map
jac code map walker
jac code walkers User
jac code slice Profile --depth 2
jac code diag
```

`slice` explicitly returns a typed neighbourhood for prompt assembly. `code` discovers the project root from the working directory. This is directly overlapping prior art and the best initial extractor. A successful map is not proof of complete graph coverage; test the particular imports, declaration/implementation splits, client code, and broken-file cases used by the target project. [Pinned command specification](https://github.com/jaseci-labs/jac/blob/v0.37.23/jac/jaclang/cli/commands/code.jac), [implementation](https://github.com/jaseci-labs/jac/blob/v0.37.23/jac/jaclang/cli/commands/impl/code.impl.jac).

## Actual Jac MCP surface and caveats

Start with `jac mcp --inspect`, then stdio `jac mcp`. Current docs describe stdio, SSE, and streamable HTTP. Resources include `jac://grammar/spec`, `jac://guide/pitfalls`, `jac://guide/*`, `jac://docs/*`, and examples. Pin resource contents together with the compiler. [Official reference](https://www.jac-lang.org/reference/mcp/).

Relevant pinned tool contracts:

| Tool | Arguments | Use |
|---|---|---|
| `validate_jac` | `code`, optional `filename` | Compilation/type-check diagnostics: `valid`, `errors`, `warnings` |
| `check_syntax` | `code` | Parse-only diagnostics |
| `search_docs` | `query`, optional `limit` (5) | Ranked snippets/resource URIs |
| `get_resource` | `uri` | Fetch full versioned reference |
| `get_ast` | `code`, optional `format` (`tree`/`json`) | Snippet AST |
| `explain_error` | `error_message` | Generic category/explanation/example |
| `run_jac` | `code`, optional `entrypoint`, `timeout` (10) | Execute snippet |
| `execute_command` | `command`, optional `args`, `timeout` (30) | Invoke Jac CLI, return success/exit code/stdout/stderr |

The same catalog includes formatting, linting, Python/Jac/JavaScript conversion, examples, commands, and graph visualization. `search_docs` counts keyword occurrences and returns short lowercased excerpts; it is not semantic graph retrieval. `explain_error` matches six regex categories and returns canned guidance, so its suggested example is not repair evidence. [Pinned tools source](https://github.com/jaseci-labs/jac/blob/v0.37.23/jac/jaclang/cli/mcp/impl/tools.impl.jac).

**Critical scope limitation:** `validate_jac` writes a temporary `.jac` file and compiles that path. Its accepted `filename` parameter is not used in the inspected compilation implementation. Passing a real path as `filename` does not establish project-relative import/layout fidelity. Compilation uses a thread timeout; timeout is not a proof that underlying compilation was terminated. Execution spawns a process, but that is not a security sandbox. Keep snippet checks distinct from project checks, tests, and application behavior. [Pinned compiler bridge](https://github.com/jaseci-labs/jac/blob/v0.37.23/jac/jaclang/cli/mcp/impl/compiler_bridge.impl.jac).

`execute_command` invokes `[sys.executable, '-m', 'jaclang', command] + args` with inherited working directory. A wrapper should bind a trusted project cwd, compiler binary, and permitted command/argument shapes. Use it for `code`, `check`, and relevant `test` invocations only after verifying those commands against the installed binary. Parse return values and diagnostics, not just transport success. [Pinned dispatcher](https://github.com/jaseci-labs/jac/blob/v0.37.23/jac/jaclang/cli/mcp/impl/tools.impl.jac).

Although current docs advertise `--mode lite` for fewer tools, **v0.37.23's inspected `disabled_tools_for_mode` and `disabled_prompts_for_mode` both return empty sets**. Do not promise smaller tool inventories from this flag; expose a curated JacBrain wrapper. [Pinned mode implementation](https://github.com/jaseci-labs/jac/blob/v0.37.23/jac/jaclang/cli/mcp/impl/mode.impl.jac).

Jac's pinned top-level license is MIT. Preserve notices if copying code; third-party bundled components require separate review before redistribution. [License](https://github.com/jaseci-labs/jac/blob/v0.37.23/LICENSE).

## Material comparisons

| Project | Material overlap | Implication for JacBrain |
|---|---|---|
| [Aider](https://aider.chat/docs/repomap.html) ([Apache-2.0](https://github.com/Aider-AI/aider)) | Graph-ranked repository map selects relevant symbols/dependencies inside a token budget, default map setting 1k tokens. | Small task-specific context from a code graph is established. Borrow budgeted ranking and compare against a plain repo-map baseline. Jac compiler extraction can be the specialization. |
| [Serena](https://github.com/oraios/serena) | MCP semantic retrieval and editing via language-server intelligence. | Another strong baseline for symbol-aware context. Jac support was not listed in the inspected README, so do not assume plug-and-play support. Current licensing is split: SolidLSP MIT, application GPL-3.0-or-later; combined distribution GPL. Do not rely on older descriptions of all-Serena-as-MIT. |
| [Code-Graph-RAG](https://github.com/vitali87/code-graph-rag) | Tree-sitter plus optional compiler facts/runtime traces into Memgraph, code retrieval and MCP. MIT core; dependencies differ. Jac absent from listed supported languages. | Code graph + RAG + MCP is not novel. Reuse Jac's own compiler facts rather than adding a Jac Tree-sitter grammar and graph database before value is shown. |
| [Graphiti](https://github.com/getzep/graphiti) | Incremental temporal knowledge graphs, episode provenance, validity/invalidation, hybrid retrieval. Apache-2.0; Python 3.10+, graph backend and inference/embedding dependencies. | Episode provenance and evolving memory are established. JacBrain's distinction would be explicit compiler/test evidence and version applicability. Graphiti is optional future infrastructure, not required for the first local tool. Its current README deprecates Kuzu. |
| [Microsoft GraphRAG](https://github.com/microsoft/graphrag) | LLM extraction of structured knowledge from text for graph-assisted retrieval. MIT; current README says largely maintenance mode and cautions about indexing cost. | Useful conceptual baseline; document community summarization is a poor first dependency for fast deterministic project-symbol retrieval. |
| [memento-mcp, lfrmonteiro99](https://github.com/lfrmonteiro99/memento-mcp) | Persistent coding-agent facts, decisions, pitfalls, session summaries; SQLite/FTS5; token-aware ranking; optional embeddings. MIT. | Even local token-budgeted project memory is prior art. Inspect evidence admission carefully before adopting: memory retrieval is not by itself executable repair validation. This is a small project whose README claims were not independently tested. |
| [Graphclaw](https://github.com/zero-abd/graphclaw) | Jac/Python graph-native assistant with sessions, consolidated memory, skills and MCP subtrees. MIT; alpha; Python 3.12+. | A Jac graph-memory agent is not itself a distinctive claim. JacBrain should remain a focused coding-context tool; no need for another general multi-agent runtime or channels dashboard. |

This search found substantial components and close combinations, not an exhaustively proven absence of an identical system. Avoid 'first', 'unique', or unqualified novelty claims.

## Recommended first implementation

1. **One project, one compiler version.** Record project ID, source-tree digest including dirty files, exact compiler version/hash, dependency lock digest, and resource snapshot hashes. Probe `jac code` and MCP inventory before depending on them.
2. **Typed graph with deterministic origins.** Import symbols/uses/walker relationships from `jac code`; connect versioned documentation, error signatures, fix episodes, and validation runs. Store graph entities/edges in Jac if demonstrating Jac is a requirement. Use a simple local keyword index, optionally SQLite FTS, without a second graph backend. Avoid an LLM entity-extraction pass over code already understood by the compiler.
3. **Two retrieval modes.** A task target uses compiler `slice` + directly relevant docs; an error target uses normalized diagnostics + matching version-scoped fix episodes. Return source locations, evidence state, reason included, token budget, and omitted context. Call it 'budgeted relevant context', not mathematically minimal context.
4. **Small MCP contract.** `get_task_context`, `find_verified_fixes`, and `record_validation` are sufficient. The trusted wrapper runs validation itself or accepts only locally verifiable run artifacts. Model assertions cannot create 'verified' facts. Leave code editing to the existing coding assistant.
5. **Evidence states.** `candidate -> reproduced -> verified_for_snapshot -> stale/superseded`. A verified fix needs a reproduced failure, exact before/after hashes, real project compile/test results, and runtime test where behavior matters. Syntax-only, type-check, project integration, and runtime behavior are separate evidence fields, not a single confidence score.
6. **Prove added value against Jac alone.** Compare: A) existing Jac MCP + `jac code slice` + docs, B) same plus flat searchable fix notes, C) JacBrain graph retrieval. Freeze model/task/compiler, run multiple trials, measure task success, recurrence of known mistakes, prompt/tool-output tokens, wall time, and evidence correctness. Include unseen tasks and version-mismatch traps. Do not optimize only prompt tokens if tool chatter or failures erase savings.

The most credible differentiator is a version-aware repair memory that can answer: **'This fix worked for this exact Jac environment, and here is the reproducible evidence and the smallest relevant project neighbourhood we chose.'** Whether graph retrieval beats simpler search remains an empirical question.
