# First context-efficiency pilot

September 29, 2026. **Smaller language-reference packets worked on four tasks.**
This is evidence for section retrieval, not yet for graph superiority or a
complete self-improving engineering agent.

| Context supplied | Reference tokens | Observed model input | Model output | Compiler + behavior |
|---|---:|---:|---:|---:|
| Three curated complete guides per task | 25,338 | 96,095 | 596 | 4/4 |
| One official MCP search response per task | 2,788 | 76,284 | 1,261 | 0/4 |
| JacBrain section retrieval + graph expansion | 6,961 | 80,319 | 592 | 4/4 |
| Same section retrieval, expansion disabled | 6,961 | Not generated | Not generated | Not independently tested |

Totals cover four tasks. JacBrain reduced reference tokens by **72.5%** and
observed model input by **16.4%** against the curated-guide baseline. Reference
counts use `tiktoken 0.12.0 / o200k_base`; these are not the model's billing
tokenizer. Observed input/output counts are from Codex CLI usage events.

## What was actually tested

The [frozen tasks](../../tasks.json) cover walkers and reports, typed fields and
initialization, dictionary/lambda sorting, and standard-library imports.
Prompts and behavioral fixtures were frozen before model trials. Every solution
was checked in a fresh project with Jac **0.37.23**, whole-project `jac check`,
and executable assertions. The date task also tested direct execution and a
quiet import. No repair rounds were allowed.

We imported **47 installed official guides**, producing **389 sections** and
**717 explicit reference edges**. Each query had a 6,000-byte packet budget.
The curated baseline used the three complete guides specified in the task
manifest. It was task-informed, not the entire documentation corpus.

Generation used the existing authenticated Codex CLI **0.154.0** default:
**gpt-6-astra**, reasoning effort **none**. A separate same-flags configuration
probe identified the model/settings; per-trial JSON events did not name them.
Only the task and selected context were supplied as task input. An external
temporary working directory kept repository fixtures and answers out of
project context. Events were inspected and contained no tool calls. Ambient
CLI skill context still appeared and varied, so this was not a pristine API
experiment. Two skill-budget notices were retained as runtime notices.

Manual review found the eight compiling solutions satisfied the requested
behavior and idioms, with one equivalent form: the graph date solution used
an explicit `__name__ == "__main__"` guard inside `with entry` instead of the
named entry form. Behavior passed; exact syntactic equivalence is not claimed.

## What this does not establish

- **No graph-specific benefit:** flat and graph packets were byte-identical
  for every task. Flat was not generated a second time. This pilot supports
  the simpler section retriever just as strongly.
- **No broad MCP comparison:** the search arm received only one `search_docs`
  result (`limit=5`) with no resource follow-up, tool interaction, or repair.
  Its four candidates had invalid Jac syntax. This does not show that a normal
  agent using Jac MCP is ineffective. The successful complete guides also
  came from Jac MCP.
- **No 73% total-token or cost claim:** CLI overhead remained substantial and
  caching differed. The graph arm reported 15,488 cached input tokens; the
  other arms reported zero. Prices were not measured.
- **No speedup:** summed generation time was 39.6 seconds for complete guides
  and 41.5 seconds for graph context. Concurrency and caching confound latency.
- **No general success-rate claim:** four guide-shaped tasks, one trial each,
  one model, no no-context control, no project repairs, and no repeated trials.

## Evidence and reproduction

[results.json](results.json) contains the corpus snapshot, context hashes,
normalized source hashes, usage, commands, exit codes and behavioral results.
[solutions/](solutions/) preserves all twelve generated candidates, including
intentionally invalid search-arm outputs. These are evaluation artifacts, not
recommended code or package sources. Hashes refer to UTF-8 text with normalized
newlines. Raw guide packets and model transcripts stay in ignored local storage;
installed source guides can be re-read from the pinned compiler.

From the repository root, with Jac 0.37.23 and an authenticated Codex CLI:

```sh
python -m pip install '.[benchmark]'
python benchmarks/evaluate.py --jac-command '["jac"]'
```

This collects context without model calls. To run a new paid/quota-consuming
pilot using the same contexts:

```sh
python benchmarks/evaluate.py --reuse-context --generate --arms full_guides mcp_search graph
```

Inspect every generated candidate before executing it. Then, in Linux/WSL:

```sh
python benchmarks/check_solutions.py --jac /absolute/path/to/jac --reviewed
```

The checker requires current generation records and matching source hashes.
Generated source executes locally; the runner is not a security sandbox. Run
untrusted candidates only in an appropriately isolated environment. See the
[runner contract](../../README.md) for fixtures, controls and Windows/WSL details.
A rerun can differ because model outputs and bundled guide contents may vary;
the recorded hashes identify this exact corpus and trial.

The next useful experiment is repeated project-level tasks with equal tool
and repair budgets, a no-context control, and dependencies that can test whether
graph expansion adds value beyond the existing section retriever.
