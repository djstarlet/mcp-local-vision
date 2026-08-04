# mcp-local-vision

MCP server that lets any text-only agent describe images by calling a local
llama.cpp vision model (tested with Qwen 3.5 4B, also works with MiniCPM-V,
LLaVA, etc.) through its OpenAI-compatible API.

No special model config needed — agents just call `vision_describe("path.png")`
and get back a text description from the vision model.

## Install via your AI agent

Tell your AI agent:

```
Install and configure mcp-local-vision -
https://github.com/djstarlet/mcp-local-vision/src/branch/main/INSTALL.md
```

The agent will fetch INSTALL.md and walk through the steps. You'll need to
provide your server URL and model alias when asked.

## Setup (manual)

The server uses the official MCP Python SDK with standard stdio framing, so it
works in **any MCP client** — Claude Code, Codex, VS Code, Cline, Cursor,
opencode, and others. It runs on Linux, macOS, and Windows.

> **Note:** on Windows, use `python` (or the full path to `python.exe`) instead
> of `python3` in the commands below.

1. Have a llama.cpp server running with a vision model (e.g. MiniCPM-V 4.6):

   ```bash
   ./llama-server -m model.gguf --mmproj mmproj.gguf \
     --host 0.0.0.0 --port 8080
   ```

2. Install the Python dependency (Python 3.10+):

   ```bash
   pip install mcp
   ```

   The server works with both mcp 1.x (FastMCP) and mcp 2.x (MCPServer), so no
   version pin is needed.

   > **Platform notes:**
   > - **Windows:** install Python from [python.org](https://www.python.org/downloads/); use `python` (or `py -3`) instead of `python3` (see the note above).
   > - **macOS:** install Python via Homebrew (`brew install python`) — the system `python3` may be a Command Line Tools stub or lack pip.
   > - **Linux:** on distros with PEP 668 (Ubuntu 23.04+, Debian 12+, Fedora) `pip install` fails with "externally-managed-environment" — use a venv (`python3 -m venv .venv && .venv/bin/pip install mcp`) or pipx, and point the registration command at the venv's python.

3. Register the server with your MCP client. Every client registers a stdio
   server as a `command` + `args` pair — for this project, always:

   ```text
   python3 /path/to/mcp-local-vision/server.py
   ```

   | Harness | Registration |
   |---|---|
   | opencode | In `opencode.jsonc`: `"mcp": { "local-vision": { "type": "local", "command": ["python3", "/path/to/mcp-local-vision/server.py"], "enabled": true } }` |
   | Claude Code | `claude mcp add local-vision -- python3 /path/to/mcp-local-vision/server.py` |
   | Codex | `codex mcp add local-vision -- python3 /path/to/mcp-local-vision/server.py` |
   | VS Code | In `.vscode/mcp.json`: `{"servers": {"local-vision": {"type": "stdio", "command": "python3", "args": ["/path/to/mcp-local-vision/server.py"]}}}` |
   | All other harnesses | Their MCP settings UI or config file — the same `command` + `args` pair (Cline, Cursor, Zed, ...) |

   See [INSTALL.md](INSTALL.md) for the full agent-driven install.

4. Restart opencode. Now any agent can call `vision_describe`.

## Subagent access

Subagents (e.g. `@vision`, `@observer`) need the `mcp` tool group to use
MCP tools. Add it to their config in `opencode.jsonc` or your agent preset:

```jsonc
"<subagent-name>": {
  "model": "...",
  "toolGroups": ["mcp", "read"]  // <-- "mcp" grants MCP tool access
}
```

This lets the subagent call `vision_describe` via any configured MCP server.

## Configuration

Create `config.json` in this directory (copy `config.json.example`):

```json
{
  "vision_api_url": "http://your-server:8080/v1/chat/completions",
  "vision_model": "OBSERVER",
  "vision_max_tokens": 2048,
  "vision_timeout": 180
}
```

`vision_model` is just a label passed to the OpenAI-compatible API. If you
run a single model directly with `llama-server`, any value works — set it to
`"model"`, `"OBSERVER"`, or whatever you like.

All values can also be overridden via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_API_URL` | `http://localhost:8080/v1/chat/completions` | OpenAI-compatible endpoint |
| `VISION_MODEL` | `OBSERVER` | Model label (any value works for single-model servers) |
| `VISION_MAX_TOKENS` | `2048` | Max response tokens |
| `VISION_TIMEOUT` | `180` | API timeout in seconds |

> **Note:** prefer `config.json` over environment variables. MCP clients spawn
> the server as a subprocess with a minimal environment allow-list (PATH, HOME,
> etc.), so custom variables like `VISION_API_URL` are not reliably inherited.
> `config.json` is always read from the server's own directory.
