---
title: MCP Local Vision Architecture
date: 2026-08-05
tags: [mcp, vision, architecture, python, bash]
---

# MCP Local Vision Architecture

This document describes the internal structure of mcp-local-vision: the layout, the request data flow, and the transport details that matter when extending or debugging the server. It is written for anyone modifying the code or diagnosing why a call fails.

The whole project is one Python file (`server.py`, ~150 lines) plus two bash helpers. The MCP protocol is handled by the official `mcp` Python SDK; `server.py` only registers one tool and calls the vision API with stdlib `urllib`.

## File Map

| File | Role |
|---|---|
| `server.py` | The MCP server: config resolution, vision API client, tool registration via `MCPServer` |
| `describe.sh` | Standalone CLI that calls the vision API directly — not part of the MCP path |
| `start.sh` | Thin wrapper: `exec python3 .../server.py` — hardcoded path, machine-specific |
| `config.json` | Machine-specific settings (gitignored) |
| `config.json.example` | Template for `config.json` |
| `INSTALL.md` | Agent-facing install instructions (clone, pip, config, registration) |
| `docs/` | This documentation set (README, architecture, api, setup, gotchas) |

## Layer Overview

`server.py` splits into three logical layers:

1. **Dependency check + config resolution** (module top) — imports the `mcp` SDK with a version shim, loads `config.json` from the repo directory, then applies env-var overrides (`VISION_API_URL`, `VISION_MODEL`, `VISION_MAX_TOKENS`, `VISION_TIMEOUT`).
2. **Vision client** (`_image_dims`, `analyze_image`) — validates the image, base64-encodes it, builds the OpenAI-compatible payload, and POSTs it with `urllib.request.urlopen` using a socket timeout. No temp file, no curl, no subprocess.
3. **MCP transport** — the `mcp` SDK's stdio server (`MCPServer("local-vision")`); `@mcp.tool()` registers `vision_describe` and the SDK handles framing, the handshake, `tools/list`, `tools/call`, and `shutdown`.

## Request Data Flow

A `vision_describe` call travels this path:

1. The agent calls `vision_describe` in any MCP client (opencode, Claude Code, Codex, VS Code, Cline, Cursor). The client spawns `server.py` as a subprocess (if not already running) and speaks the standard MCP stdio protocol.
2. The SDK runs the stdio server loop: it performs the `initialize` handshake, answers `tools/list` from the registered tools, and dispatches `tools/call` to the `vision_describe` handler.
3. `analyze_image()`:
   - Verifies the file exists; returns an error string otherwise.
   - Runs `_image_dims()` (PIL-free PNG/JPEG header parse) and rejects images under 10×10 px or with an aspect ratio over 50:1 as likely corrupt.
   - Reads the file and base64-encodes it.
   - Builds the OpenAI-compatible payload and POSTs it to `OBSERVER_URL` with `urllib.request.urlopen(..., timeout=TIMEOUT)`.
   - Parses the response and returns `message.content`, falling back to `message.reasoning_content` when `content` is empty (reasoning models put the answer there).
4. The SDK serializes the returned string as a text tool result and sends it back over stdio. Errors are returned as plain-text strings inside the result — not as protocol errors.

```text
agent ──tools/call──▶ any MCP client ──MCP stdio──▶ server.py (mcp SDK)
                                                      │
                       ┌──────────────────────────────┤
                       ▼                              ▼
                sanity checks               urllib POST ──▶ llama-server
                base64 encode                     (OpenAI-compatible API)
                       │                              │
                       └──────────◀── text description ─┘
                       ▼
                tool result text ──▶ client ──▶ agent
```

## MCP Transport Details

- **Framing:** official MCP Python SDK stdio transport with standard MCP framing — interoperable with any MCP client. The old hand-rolled newline-delimited JSON transport no longer exists.
- **SDK version shim:** `server.py` imports `MCPServer` from `mcp.server` (mcp ≥ 2.0, where FastMCP was renamed) and falls back to `FastMCP` from `mcp.server.fastmcp` (mcp 1.x). Both are aliased as `MCPServer`. If the `mcp` package is missing, the server prints an install hint to stderr and exits with code 1.
- **Lifecycle:** the SDK handles `initialize`, `tools/list`, `tools/call`, `shutdown`, notifications, and error codes. `server.py` only registers `vision_describe` via `@mcp.tool()` and calls `mcp.run()`.
- **Server identity:** `MCPServer("local-vision")`; protocol version and server version are SDK defaults.

## Platforms

- **MCP path** (`server.py` + the `mcp` package) is pure Python and runs on Linux, macOS, and Windows with Python 3.10+ — no bash, curl, or temp-file dependency.
- **Bash helpers** (`describe.sh`, `start.sh`) are Linux/macOS only; on Windows they would need Git Bash or WSL, and they are not required for MCP use.
- **llama.cpp backend** runs on all three: native Windows builds, macOS (Metal), Linux (CUDA/ROCm/CPU).

## Vision API Payload

The request sent to the model endpoint mirrors the OpenAI chat-completions format:

```json
{
  "model": "OBSERVER",
  "messages": [{
    "role": "user",
    "content": [
      {"type": "text", "text": "Describe this image in detail."},
      {"type": "image_url", "image_url": {
        "url": "data:image/png;base64,<base64-image>"
      }}
    ]
  }],
  "max_tokens": 2048,
  "reasoning_budget": 0
}
```

> **Note:** the data URI mime type is hardcoded to `image/png` even for JPEG inputs. llama.cpp tolerates this in practice; it only matters if you point the server at a stricter OpenAI-compatible backend.

## Image Pre-Flight Constants

| Constant | Value | Purpose |
|---|---|---|
| `MIN_DIM` | `10` | Images smaller than 10×10 px are skipped as corrupt/placeholder |
| `MAX_RATIO` | `50` | Images with width/height ratio over 50:1 are skipped as corrupt |
| `TIMEOUT` | `180` (default) | Socket timeout passed to `urllib.request.urlopen` |

## See Also

- [README](../README.md) — what the server is and how to use it
- [api](api.md) — tool definitions and configuration reference
- [gotchas](gotchas.md) — known sharp edges in this design
