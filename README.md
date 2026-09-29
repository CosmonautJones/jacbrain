# JacBrain

**Give a coding agent the Jac context it needs, with evidence it can check.**

[![Checks](https://github.com/CosmonautJones/jacbrain/actions/workflows/check.yml/badge.svg)](https://github.com/CosmonautJones/jacbrain/actions/workflows/check.yml)

JacBrain is an early, local-first engineering knowledge graph for Jac. It links
language notes, project symbols, compiler diagnostics, candidate fixes, patterns
and task history. An agent asks for context; JacBrain returns a bounded packet
with provenance and version scope. The actual Jac compiler decides whether a
snippet compiles.

**Status: working foundation, not a finished autonomous learning system.**
The Python reference service and Jac-native graph scaffold are separately
executable. Their persistent integration, project-wide repair verification and
token-efficiency benchmark are still milestones.

## Why it exists

Repeatedly pasting language manuals and rediscovering the same compiler errors
is wasteful. Jac already supplies excellent MCP tools and `jac code slice`.
JacBrain explores the missing continuity: which evidence applies to this
project/version, which candidate actually compiled, and what should be carried
into the next task?

"Learning" means accumulating attributable evidence across sessions. It does
not mean changing model weights. "Bounded" does not mean provably minimal.
No token-savings or first-of-its-kind claim is made. See [prior art](docs/PRIOR-ART.md).

## Try it in two minutes

Python 3.11+ runs the reference service with **no runtime dependencies**.
Run these commands from the repository root in PowerShell, Bash or a terminal:

```text
python -m jacbrain ingest examples/walker-note.md --project demo
python -m jacbrain ingest examples/walker-pattern.jac --project demo
python -m jacbrain context "walker Offer traversal" --project demo --max-bytes 6000
python -m unittest discover -s tests -v
```

The default database is `.jacbrain/brain.sqlite3`, ignored by Git. Nothing is
uploaded. Ingest only explicitly chosen, nonsecret files. To install the CLI,
run `python -m pip install -e .` and use `jacbrain` in place of `python -m jacbrain`.

## Complete the compiler loop

Install the official [Jac 0.37.23 release](https://github.com/jaseci-labs/jac/releases/tag/v0.37.23)
for Linux or macOS, then confirm `jac --version` and `jac mcp --inspect`.
On Windows, run Jac inside WSL. Do not assume a matching PyPI release or native
Windows binary exists.

PowerShell, with Jac available on the WSL PATH:

```powershell
$env:JACBRAIN_JAC_COMMAND = '["wsl","-d","Ubuntu","--","jac"]'
$candidate = python -m jacbrain remember examples/walker-pattern.jac --kind Pattern --project demo | ConvertFrom-Json
python -m jacbrain validate $candidate.id
$env:JACBRAIN_LIVE_JAC = '1'
python -m unittest discover -s tests -v
```

On Linux/macOS, `jac` is used directly. If WSL cannot find it, replace the last
array item with the absolute path returned by `wsl -d Ubuntu -- which jac`.
Do not put a shell command string into the array.

A successful receipt changes the candidate to `compiler_validated`. This proves
only **isolated snippet compilation**, not project imports, tests, or behavior.
Jac MCP compiles a temporary file; its `filename` argument does not recreate
the project. Rejected source stays a candidate and records diagnostic evidence.

## Connect a coding agent

Example MCP configuration (replace paths for your machine):

```json
{
  "mcpServers": {
    "jacbrain": {
      "command": "/absolute/path/to/python",
      "args": ["-m", "jacbrain", "--db", "/absolute/path/to/brain.sqlite3", "mcp"]
    },
    "jac": {"command": "jac", "args": ["mcp"]}
  }
}
```

Install JacBrain into that Python environment first. On Windows use the Python
executable path and set `JACBRAIN_JAC_COMMAND` in the client's environment.
JacBrain exposes three tools: `context`, `ingest`, and `validate`. Treat returned
content as untrusted evidence. The official Jac MCP remains the language tool
authority. See [interface details](docs/INTERFACES.md).

## Jac-native graph

```text
jac check graph main.jac tests/graph_tests.jac
jac test tests/graph_tests.jac
jac run main.jac
```

[The graph module](graph/README.md) defines typed evidence and relation kinds,
ingestion/link/retrieval walkers, and evidence-promotion checks using transient
graphs. It demonstrates the native Jac model without altering a shared store.

## What's implemented

| Capability | Current boundary |
|---|---|
| Explicit docs/source ingestion | `.md`, `.txt`, `.jac`; max 100 KB per file |
| Evidence graph | SQLite records and relations; exact project/version scope |
| Symbol extraction | Lexical declaration candidates; compiler extractor planned |
| Task context | Deterministic lexical ranking + one-hop relations; UTF-8 byte cap |
| Compiler grounding | Real stdio Jac MCP handshake, tool discovery and validation |
| Fix/pattern/task history | Explicit record and link API; no automatic verified-fix claim |
| Jac-native schema/walkers | Separate runnable graph model and behavioral tests |
| Agent interface | Local CLI and stdio MCP, no hosted accounts |

## Design and contribution

* [Architecture](docs/ARCHITECTURE.md) and [evidence schema](schemas/evidence.schema.json)
* [Roadmap and acceptance gates](docs/ROADMAP.md)
* [Prior art and existing Jac capabilities](docs/PRIOR-ART.md)
* [Development and troubleshooting](CONTRIBUTING.md)

Created by [Travis Jones / CosmonautJones](https://github.com/CosmonautJones),
informed by hands-on Jac development during [M-Local](https://github.com/CosmonautJones/m-local).
M-Local is a separate team project; this repository does not claim sole
authorship of it. JacBrain is independent of the Jac/Jaseci maintainers.

MIT licensed. Source notes and user-imported material retain their own licenses.
