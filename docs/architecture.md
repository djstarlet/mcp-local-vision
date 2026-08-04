---
title: MCP Local Vision Architecture
date: 2026-08-05
tags: [mcp, vision, architecture, python, bash]
---

# MCP Local Vision Architecture

This document describes the internal structure of mcp-local-vision: the layout, the request data flow, and the transport details that matter when extending or debugging the server. It is written for anyone modifying the code or diagnosing why a call fails.

The whole project is one Python file (`server.py`, ~230 lines) plus two bash helpers. There is no framework — the MCP protocol is implemented by hand over stdio.

## File Map

| File | Role |
|---|---|
| `server.py` | The MCP server: config resolution, vision API client, stdio message loop |
| `describe.sh` | Standalone CLI that calls the vision API directly (no MCP) |
| `start.sh` | Thin wrapper: `exec python3 .../server.py` — hardcoded path, machine-specific |
| `config.json` | Machine-specific settings (gitignored) |
| `config.json.example` | Template for `config.json` |
| `INSTALL.md` | Agent-facing install instructions (clone, config, opencode registration) |

## Layer Overview

`server.py` splits into three logical layers:

1. **Config resolution** (module top, lines 12–23) — loads `config.json` from the repo directory, then applies env-var overrides (`VISION_API_URL`, `VISION_MODEL`, `VISION_MAX_TOKENS`, `VISION_TIMEOUT`).
2. **Vision client** (`_image_dims`, `analyze_image`) — validates the image, base64-encodes it, builds the OpenAI-compatible payload, and calls the model via `curl` subprocess.
3. **MCP transport** (`send`, `recv`, `main`) — newline-delimited JSON-RPC over stdio; implements `initialize`, `tools/list`, `tools/call`, and `shutdown`.

## Request Data Flow

A `vision_describe` call travels this path:

1. The agent sends `tools/call` to opencode, which spawns/uses the server process and writes the JSON-RPC message to its stdin.
2. `recv()` reads one newline-delimited JSON line from stdin.
3. `main()` matches the method:
   - `tools/list` → returns the `vision_describe` tool definition.
   - `tools/call` → extracts `file_path` and `prompt`, calls `analyze_image()`.
4. `analyze_image()`:
   - Verifies the file exists; returns an error string otherwise.
   - Runs `_image_dims()` (PIL-free PNG/JPEG header parse) and rejects images under 10×10 px or with an aspect ratio over 50:1 as likely corrupt.
   - Reads the file and base64-encodes it.
   - Writes the JSON payload to `/tmp/mcp-vision-payload.json` — a temp file, not the command line, to avoid `argument list too long` on large images.
   - Runs `curl -s --max-time <TIMEOUT> -d @/tmp/mcp-vision-payload.json <url>` via subprocess.
   - Parses the response and returns `message.content`, falling back to `message.reasoning_content` when `content` is empty (reasoning models put the answer there).
5. The result string is wrapped in `{"type": "text", "text": ...}` and sent back as the tool result. Errors are returned as plain text strings inside the result — not as JSON-RPC errors.

```text
agent ──tools/call──▶ opencode ──stdio NDJSON──▶ server.py
                                                  │
                     ┌────────────────────────────┤
                     ▼                            ▼
              sanity checks            curl ──▶ llama-server (OpenAI API)
              base64 encode                    (vision model + mmproj)
                     │                            │
                     └────────◀─── text description ─┘
                     ▼
              tool result text ──▶ opencode ──▶ agent
```

## MCP Transport Details

- **Framing:** newline-delimited JSON (NDJSON) on stdin/stdout — **not** the 4-byte length-prefixed framing used by the official MCP SDKs. This matches opencode's expectation, but clients that use the SDK framing will not work.
- **Protocol version:** `2024-11-05`; capabilities advertise `tools` only.
- **Server identity:** `local-vision` v1.0.0.
- **First-message rule:** `main()` unconditionally treats the first message received as `initialize` and replies with the init result, regardless of its actual method. Every subsequent message goes through the dispatch loop.
- **Notifications:** messages without an `id` are silently dropped.
- **Unknown methods and tools** get a JSON-RPC error `-32601` ("Unknown method/tool").
- **Shutdown:** a `shutdown` request returns `null` and breaks the loop, ending the process.

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
| `TIMEOUT` (subprocess) | `TIMEOUT + 20` | `subprocess.run` timeout is the curl timeout plus 20 s slack |

## See Also

- [README](README.md) — what the server is and how to use it
- [api](api.md) — tool definitions and configuration reference
- [gotchas](gotchas.md) — known sharp edges in this design
