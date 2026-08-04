---
title: MCP Local Vision Setup
date: 2026-08-05
tags: [mcp, vision, setup, opencode, llama-cpp]
---

# MCP Local Vision Setup

This document covers installing and configuring mcp-local-vision: prerequisites, the llama.cpp vision backend, registration with opencode, and verification. Follow it when setting the server up on a new machine or re-registering it after a move.

The server has no Python dependencies beyond the standard library — setup is mostly about the model backend and the client registration.

## Prerequisites

1. **Python 3** with `json`, `base64`, `struct`, `subprocess` — all stdlib.
2. **`curl`** on `PATH` — the server shells out to it for the API call.
3. **A running llama.cpp server** with a vision model loaded (see [Start the Vision Backend](#start-the-vision-backend)).
4. **opencode** (or any NDJSON-over-stdio MCP client) to register the server in.

## Install

1. Clone the repository:

   ```bash
   git clone <repo-url> ~/projects/mcp-local-vision
   cd ~/projects/mcp-local-vision
   ```

2. Create `config.json` from the example:

   ```bash
   cp config.json.example config.json
   ```

3. Edit `config.json` to point at your model server:

   ```json
   {
     "vision_api_url": "http://localhost:8080/v1/chat/completions",
     "vision_model": "OBSERVER",
     "vision_max_tokens": 2048,
     "vision_timeout": 180
   }
   ```

   `vision_model` is only a label passed in the request body — for a single-model `llama-server` any value works. Set it to the model alias if you use a multi-model gateway.

4. Register the MCP server in the project's `opencode.jsonc` (or `.opencode.jsonc`):

   ```jsonc
   "mcp": {
     "local-vision": {
       "type": "local",
       "command": ["python3", "/path/to/mcp-local-vision/server.py"],
       "enabled": true
     }
   }
   ```

5. Restart opencode — MCP configuration is not hot-reloaded.

## Start the Vision Backend

Run llama.cpp with both the model and its vision projector (`--mmproj`):

```bash
./llama-server -m model.gguf --mmproj mmproj.gguf \
  --host 0.0.0.0 --port 8080
```

On this machine the backend is `llama-server-host` at `http://localhost:8080/v1/` with model `OBSERVER` (Qwen3.5-4B). See [Setup Overview](../../setup.md) for the full rig.

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

Every config key can be overridden per-process without touching `config.json` — useful for pointing the server at a different backend in tests:

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

## Verify

1. **Check the model endpoint directly** (bypasses MCP entirely):

   ```bash
   ./describe.sh /path/to/test-image.png
   ```

   A description on stdout means the backend and config are correct.

2. **Exercise the MCP protocol** by piping NDJSON messages into the server:

   ```bash
   printf '%s\n' \
     '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
     '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
     '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"vision_describe","arguments":{"file_path":"/path/to/test-image.png"}}}' \
     '{"jsonrpc":"2.0","id":4,"method":"shutdown"}' \
     | python3 /path/to/mcp-local-vision/server.py
   ```

   Expect four JSON lines: init result, tool list, the description, and `null` for shutdown.

3. **From an agent:** restart opencode, then ask it to describe an image — the agent should call `vision_describe` on its own.

## See Also

- [README](../README.md) — overview and quick start
- [api](api.md) — configuration reference tables
- [gotchas](gotchas.md) — setup-time pitfalls
