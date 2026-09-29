# Verification record

September 29, 2026. Jac 0.37.23; Windows Python 3.13 and WSL Ubuntu Python 3.12.

## Checks performed

* Python unit and integration suite, including real Jac MCP acceptance and
  rejection, source supersession, byte-budget excerpts, scoped graph links,
  malformed upstream catalogs, and blocked subprocess pipe regressions.
* Jac source check: six files passed; four nonfatal checker/style warnings.
* Jac native graph tests: six passed. Demo executed and printed the synthetic
  task, diagnostic, fix and concept context.
* CLI explicit ingestion and context query executed against a disposable local
  SQLite store. Live validation used the installed Jac MCP stdio process.
* GitHub Actions runs Python 3.11/3.13 on Windows/Linux, installs the package,
  checks Jac sources, executes graph tests/demo, and requires live MCP tests.

Use the [Actions page](https://github.com/CosmonautJones/jacbrain/actions)
for exact commit-specific results. Passing a previous commit is not evidence
that later changes passed.

## Known limits

No tokenizer benchmark, compiler-resolved project ingestion, real-project repair
replay, multi-user service, hostile-code sandbox, or Jac/SQLite persistence
bridge is verified. Four Jac warnings remain around edge predicates/typing and
an empty-parenthesis style hint. Their tested graph behavior passes; warning-free
compilation is not claimed.

The mock-server tests probe transport failures; they are not compiler evidence.
The live compiler test is separate and required in CI. None of these checks
establishes business or runtime correctness for an arbitrary remembered pattern.
