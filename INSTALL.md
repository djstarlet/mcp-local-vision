# Install mcp-local-vision

Instructions for an AI agent.

## Required from user

The user must provide:
- **llama.cpp server URL** — e.g. `http://localhost:8080/v1/chat/completions`
- **Vision model name** — the model label for llama.cpp's API (any value works for single-model servers), e.g. `OBSERVER`
- **Clone path** — where to clone the repo (default: `~/projects/mcp-local-vision`)

If the user didn't include these, ask for them before proceeding.

## Steps

### 1. Clone the repo

```bash
git clone https://github.com/djstarlet/mcp-local-vision.git <clone-path>
```

### 2. Install the Python dependency

Python 3.10+ is required. The server works with both mcp 1.x (FastMCP) and
mcp 2.x (MCPServer) via an import shim — no version pin:

```bash
pip install mcp
```

> **Platform notes:**
> - **Windows:** install Python from python.org; use `python` (or `py -3`) in registration commands, not `python3`.
> - **macOS:** install Python via Homebrew (`brew install python`) — the system `python3` may be a Command Line Tools stub or lack pip.
> - **Linux:** on distros with PEP 668 (Ubuntu 23.04+, Debian 12+, Fedora) `pip install` fails with "externally-managed-environment" — use a venv (`python3 -m venv .venv && .venv/bin/pip install mcp`) or pipx, and point the registration pair at the venv's python.

### 3. Create config.json

Write `<clone-path>/config.json`:

```json
{
  "vision_api_url": "<server URL from user>",
  "vision_model": "<model name from user>",
  "vision_max_tokens": 2048,
  "vision_timeout": 180
}
```

### 4. Register the server with your MCP client

Every MCP client registers a stdio server the same way: a **`command`** plus
**`args`** pair that spawns the server process. For this project the pair is
always:

```text
python3 <clone-path>/server.py
```

Everything else — config file shape, CLI syntax — is just that pair written in
the client's own format.

> **Note:** on Windows, use `python` (or the full path to `python.exe`) instead
> of `python3` in the pair above and in every registration command below.

| Harness | Registration |
|---|---|
| opencode | In `opencode.jsonc`: `"mcp": { "local-vision": { "type": "local", "command": ["python3", "<clone-path>/server.py"], "enabled": true } }` |
| Claude Code | `claude mcp add local-vision -- python3 <clone-path>/server.py` |
| VS Code | In `.vscode/mcp.json`: `{"servers": {"local-vision": {"type": "stdio", "command": "python3", "args": ["<clone-path>/server.py"]}}}` |
| Codex / Cline / Cursor / Zed / others | Their MCP settings UI or config file — same `command` + `args` pair |

Every harness on the market uses the same pair — if yours isn't listed, put
`python3 <clone-path>/server.py` into its MCP/stdio server settings.

### 5. Test it

Restart or reload the MCP client, then ask any agent to call
`vision_describe("<path to an image>")` and confirm a description comes back.
For a scripted SDK-client smoke test, see [docs/setup.md](docs/setup.md).
