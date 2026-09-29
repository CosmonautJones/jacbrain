# Development

Python 3.11+; all reference-service tests use the standard library:

```text
python -m unittest discover -s tests -v
python -m compileall -q jacbrain
```

Real Jac integration is opt-in locally and mandatory in the Linux CI job.
Set `JACBRAIN_LIVE_JAC=1`, make `jac` 0.37.23 available, then run the suite.
On Windows, set `JACBRAIN_JAC_COMMAND` to the WSL argv array in the README.
The tests create disposable SQLite stores; they do not touch your default DB.

Before changing Jac files, consult `jac guide jac-core-cheatsheet`,
`jac guide jac-types` and the relevant walker/node guide. Run `jac check`,
`jac test tests/graph_tests.jac` and `jac run main.jac` from this root.

Keep evidence scope explicit. Do not mark a fix successful because it compiles.
Never commit local databases, source secrets, imported private docs or credentials.
Use small changes with behavioral tests and document failure modes.

## Troubleshooting

* **Jac unavailable:** check `jac --version` or the WSL command path. Python-only
  features still work; no validation promotion occurs without the compiler.
* **Version mismatch:** re-ingest under the actual version after reviewing
  applicability. Do not relabel old receipts to make a check pass.
* **Empty context:** confirm project/version, query words, and byte budget.
  Long records use matching excerpts; tiny budgets may omit even their metadata.
* **Imports fail during validation:** the MCP tool checks an isolated temporary
  snippet. Run project-level `jac check` and tests separately.
* **MCP client cannot import jacbrain:** install this repo with the same Python
  executable configured in your client, or set its working directory to this repo.
* **Database locked:** stop concurrent writers and retry; this MVP is a local
  single-user reference service, not a multi-tenant database server.
