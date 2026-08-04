---
title: MCP Local Vision Setup
date: 2026-08-05
tags: [mcp, vision, setup, opencode, llama-cpp]
---

# MCP Local Vision Setup

This document covers installing and configuring mcp-local-vision: prerequisites, the llama.cpp vision backend, registration with an MCP client, and verification. Follow it when setting the server up on a new machine or re-registering it after a move.

Beyond the `mcp` package the server has no Python dependencies — the vision API call uses stdlib `urllib`. Setup is mostly about the model backend and the client registration.

## Prerequisites

1. **Python 3.10+**.
2. **The `mcp` package** — `pip install mcp`. Works with both mcp 1.x (FastMCP) and 2.x (MCPServer); no version pin.
3. **A running llama.cpp server** with a vision model loaded (see [Start the Vision Backend](#start-the-vision-backend)).
4. **An MCP client** — opencode, Claude Code, Codex, VS Code, Cline, Cursor, or any client that speaks standard MCP stdio.

## Install

1. Clone the repository:

   ```bash
   git clone <repo-url> ~/projects/mcp-local-vision
   cd ~/projects/mcp-local-vision
   ```

2. Install the dependency:

   ```bash
   pip install mcp
   ```

3. Create `config.json` from the example:

   ```bash
   cp config.json.example config.json
   ```

4. Edit `config.json` to point at your model server:

   ```json
   {
     "vision_api_url": "http://localhost:8080/v1/chat/completions",
     "vision_model": "OBSERVER",
     "vision_max_tokens": 2048,
     "vision_timeout": 180
   }
   ```

   `vision_model` is only a label passed in the request body — for a single-model `llama-server` any value works. Set it to the model alias if you use a multi-model gateway.

5. Register the MCP server in the project's `opencode.jsonc` (or `.opencode.jsonc`):

   ```jsonc
   "mcp": {
     "local-vision": {
       "type": "local",
       "command": ["python3", "/path/to/mcp-local-vision/server.py"],
       "enabled": true
     }
   }
   ```

   For other harnesses, see the one-liners in [INSTALL.md](../INSTALL.md) (`claude mcp add ...`, VS Code `.vscode/mcp.json`).

   > **Note:** on Windows, use `python` (or the full path to `python.exe`) as the command — `python3` usually does not exist there.

6. Restart the client — MCP configuration is not hot-reloaded.

## Start the Vision Backend

Run llama.cpp with both the model and its vision projector (`--mmproj`):

```bash
./llama-server -m model.gguf --mmproj mmproj.gguf \
  --host 0.0.0.0 --port 8080
```

On this machine the backend is `llama-server-host` at `http://localhost:8080/v1/` with model `OBSERVER` (Qwen3.5-4B).

> **Warning:** without `--mmproj` the server starts but rejects image content — `vision_describe` then returns the API's error text.

## Grant Subagent Access

Subagents must opt into MCP tools. Add the `mcp` tool group to their config:

```jsonc
"<subagent-name>": {
  "model": "...",
  "toolGroups": ["mcp", "read"]  // "mcp" grants MCP tool access
}
```

## Environment Variables

Every config key can be overridden per-process without touching `config.json` — useful when running the server manually against a different backend:

```bash
VISION_API_URL=http://localhost:8080/v1/chat/completions \
VISION_MODEL=OBSERVER \
VISION_MAX_TOKENS=2048 \
VISION_TIMEOUT=180 \
python3 server.py
```

| Env var | Overrides | Default |
|---|---|---|
| `VISION_API_URL` | `vision_api_url` | `http://localhost:8080/v1/chat/completions` |
| `VISION_MODEL` | `vision_model` | `OBSERVER` |
| `VISION_MAX_TOKENS` | `vision_max_tokens` | `2048` |
| `VISION_TIMEOUT` | `vision_timeout` | `180` |

> **Warning:** when the server is spawned by an MCP client, custom env vars are not reliably inherited (clients pass a minimal environment). For client-launched runs, put settings in `config.json` instead.

## Verify

1. **Check the model endpoint directly** (bypasses MCP entirely):

   ```bash
   ./describe.sh /path/to/test-image.png
   ```

   A description on stdout means the backend and config are correct. Note this script is independent of the MCP server.

2. **Exercise the MCP protocol** with a small Python SDK client. This is the mcp 1.x form (`ClientSession`); on mcp 2.x the class was renamed to `Client` — adjust the import:

   ```python
   import asyncio

   from mcp import ClientSession, StdioServerParameters
   from mcp.client.stdio import stdio_client

   async def main():
       params = StdioServerParameters(
           command="python3",
           args=["/path/to/mcp-local-vision/server.py"],
       )
       async with stdio_client(params) as (read, write):
           async with ClientSession(read, write) as session:
               await session.initialize()
               result = await session.call_tool(
                   "vision_describe",
                   {"file_path": "/path/to/test-image.png"},
               )
               print("\n".join(c.text for c in result.content))

   asyncio.run(main())
   ```

   Expect the model's description on stdout. On Windows, use `command="python"`.

3. **From an agent:** restart the client, then ask it to describe an image — the agent should call `vision_describe` on its own.

## See Also

- [README](../README.md) — overview and quick start
- [api](api.md) — configuration reference tables
- [gotchas](gotchas.md) — setup-time pitfalls
