# Compiler and coding-agent setup

Start with the [README quick start](../README.md#try-it). The steps below add
real Jac compiler validation and connect JacBrain to a coding agent. Run commands
from the repository root.

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
authority. See [interface details](INTERFACES.md).

