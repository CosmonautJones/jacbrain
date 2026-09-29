# Frozen Jac task pilot

`tasks.json` contains four independently selected coding tasks for Jac 0.37.23.
They were written from the installed compiler's official guides before running
model/retrieval comparisons. They are a small diagnostic pilot, not a
representative benchmark or proof that graph retrieval improves coding.

| Task | Behavioral checks | Baseline guides beyond `jac-essentials` |
|---|---|---|
| Walker traversal and reports | Empty graph, traversal through a disabled bridge, detached-node exclusion, one sorted report, independent repeated spawns | `jac-walker-patterns`, `jac-node-edge-patterns` |
| Typed fields and initialization | Required arguments, quantity default, computed subtotal, explicit tags, isolated list defaults, zero quantity | `jac-has-fields`, `jac-types` |
| Dictionary and lambda sorting | Inclusive threshold, negative scores, alphabetical ties, empty result/input, unchanged dictionary | `jac-core-cheatsheet`, `jac-types` |
| Standard library imports | Leap years, same day, reverse dates, invalid-date exception, quiet import and direct-run message | `jac-core-cheatsheet`, `jac-python-interop` |

## Runner contract

1. Create a **fresh project directory for every task/condition/trial**. Write
   `shared_files`, then the task's `files`, replacing the single `{{solution}}`
   placeholder with the model's proposed source. Do not modify the assertions.
2. Send the model only `prompt` and the selected documentation context. Keep
   harnesses, expected concepts, relevant-guide labels, acceptance outputs, and
   reference solutions out of its input. Reference solutions are not in this
   repository. Use the same output-format instruction in every condition.
3. Run the installed pinned compiler from that directory with `jac check`
   **without file arguments**. Checking only the harness does not check imported
   module bodies in this compiler version. `check_files` lists the relevant
   files for inspection; it is not permission to skip whole-project checking.
4. Run `jac run --backend python --no-cache <run_file>`. Require exit code zero,
   no timeout, and `success_marker` as a complete stdout line. Reject any line
   listed in `forbidden_stdout`. Walker reports normally print their values;
   extra report output alone is not failure.
5. Run every `additional_runs` entry with the same flags and require its stated
   complete stdout lines and exit code zero. For the direct date-module run,
   the complete nonempty stdout must be exactly `date helper ready`.
6. Save source, compiler version, commands, exit codes, stdout/stderr, timeouts,
   context, prompt hash, fixture hash, and generation usage. A success marker
   alone cannot override failed assertions, a nonzero exit, or timeout.

The manifest's command names are logical commands. Substitute the configured
Jac executable. On the verified Windows/WSL machine, the compiler executable is
`/home/ravesty/.local/bin/jac` inside Ubuntu; bare `wsl -- jac` was not on PATH.
The run flag verified here is `--backend python`, not `--no-autonative`.
No web packages or model provider credentials are needed to execute fixtures.

Each command has a 45-second outer timeout. The execution environment must
enforce that timeout and terminate process descendants. Jac compilation and
execution are not security sandboxes: run model-generated candidates only in
an appropriately isolated evaluation environment without secrets.

## Freeze and comparisons

The initial prompts and fixture templates were frozen on 2026-09-29.
`prompt_sha256` hashes the UTF-8 prompt; `fixtures_sha256` hashes `files` serialized
with sorted keys and compact JSON separators. If an actual harness bug requires
a change, version the manifest and rerun every condition. Do not alter prompts,
expected guide concepts, guide selections, assertions, or thresholds to improve
retriever results.

`baseline_guides` are a task-informed **curated documentation baseline**, not
an automatically selected baseline. Use their installed contents verbatim and
record guide hashes. For a full-documentation baseline, define one common
corpus up front and provide the same corpus for every task. A no-context
baseline and lexical retrieval are useful additional controls.

Keep model/version, generation settings, output-token allowance, task wording,
and retry policy constant. Use matched repeated trials and report every failure.
The first pilot can use one generation with no repairs; any repair-loop study
must give every condition the same compiler feedback and retry budget. Charge
repair context and output toward total usage, including failed trials.

Record **actual provider input/output usage** where available. A UTF-8 byte
count is not a token count. If estimating tokens offline, name the tokenizer
and label estimates. Report context size alongside behavioral success,
compiler success, latency, and total attempt cost. Four easy, guide-shaped tasks
can expose regressions but cannot establish general superiority or percentage
improvements across Jac development.

`expected_concepts` are diagnostic relevance labels only. They are not a
complete gold-standard retrieval set and must not become ranking features.
`manual_constraints` identify requested idioms that behavioral outputs alone
cannot prove, such as use of a typed lambda or postinit rather than an alternate
implementation. Report manual constraint compliance separately, or add a
compiler-AST validator in a later version; do not silently call behavior-only
success full instruction compliance.

## Fixture feasibility

All four frozen harnesses were checked with real Jac 0.37.23 on Ubuntu/WSL.
Independent reference implementations passed whole-project `jac check` and
the executable assertions; the date helper also passed its direct-run check.
Reference implementations and raw feasibility logs were kept outside this
repository, not supplied to a coding model. This verifies fixture feasibility,
not model performance or retrieval quality.
