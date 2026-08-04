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

### 4. Add to opencode.jsonc

Find the project's `opencode.jsonc` (or `.opencode.jsonc`) and add:

```jsonc
"mcp": {
  "local-vision": {
    "type": "local",
    "command": ["python3", "<clone-path>/server.py"],
    "enabled": true
  }
}
```

### 5. Register in other harnesses

The server speaks the standard MCP stdio protocol, so it works in any MCP
client. Register it with:

- **Claude Code:**

  ```bash
  claude mcp add local-vision -- python3 <clone-path>/server.py
  ```

- **VS Code:** add a stdio entry to `.vscode/mcp.json`:

  ```json
  {
    "servers": {
      "local-vision": {
        "type": "stdio",
        "command": "python3",
        "args": ["<clone-path>/server.py"]
      }
    }
  }
  ```

- **Codex / Cline / Cursor / opencode:** use their MCP config UI or config
  file with the same `command` + `args` pair.

> **Note:** on Windows, use `python` (or the full path to `python.exe`) instead
> of `python3` in every command above.
