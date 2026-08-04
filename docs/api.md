---
title: MCP Local Vision API Reference
date: 2026-08-05
tags: [mcp, vision, api, reference]
---

# MCP Local Vision API Reference

This document is the reference for the public surface of mcp-local-vision: the MCP tool it exposes, the protocol lifecycle, and every configuration option. Use it when wiring the server into a client, writing agent prompts, or tuning behavior.

The server exposes exactly one tool, `vision_describe`, registered with the official MCP Python SDK over stdio.

## Requirements

- **Python 3.10+** — the server uses `int | None` union syntax and `tuple[int, int]` generics.
- **`mcp` package** — install with `pip install mcp`. No version pin: the import shim accepts both mcp 1.x (`FastMCP`) and mcp 2.x (`MCPServer`, the renamed `FastMCP`).
- **Platforms** — runs on Linux, macOS, and Windows: the server is pure Python, so any Python 3.10+ environment works.

## Server Identity

| Property | Value |
|---|---|
| Name | `local-vision` |
| Version | SDK default (not set in code) |
| Protocol version | SDK-negotiated (MCP 2024-11-05 line) |
| Transport | official MCP SDK stdio (standard MCP framing) |
| Capabilities | tools (auto-discovered from `@mcp.tool()`) |

## Tool: `vision_describe`

Analyzes an image with the local vision model and returns a text description.

| Param | Type | Required | Default | Description |
|---|---|---|---|---|
| `file_path` | string | yes | — | Absolute path to the image file (PNG, JPG, etc.) |
| `prompt` | string | no | `Describe this image in detail.` | Custom prompt sent to the model |

Declared input schema (as returned by `tools/list`):

```json
{
  "type": "object",
  "properties": {
    "file_path": {
      "type": "string",
      "description": "Absolute path to the image file (PNG, JPG, etc.)"
    },
    "prompt": {
      "type": "string",
      "description": "Optional custom prompt. Default: 'Describe this image in detail.'"
    }
  },
  "required": ["file_path"]
}
```

### Result

A tool result with a single text content item. The text is either the model's description or an error/skip message — see [Error Behavior](#error-behavior).

```json
{
  "content": [{"type": "text", "text": "The image shows... "}]
}
```

> **Note:** for reasoning models, the answer may arrive in `reasoning_content` rather than `content`. The server falls back to `reasoning_content` whenever `content` is empty.

## MCP Methods

| Method | Handled by | Response |
|---|---|---|
| `initialize` | SDK | Protocol handshake (SDK-managed) |
| `tools/list` | SDK, from `@mcp.tool()` | The `vision_describe` tool definition |
| `tools/call` | `vision_describe` handler | Text content with the description |
| `shutdown` | SDK | Graceful exit |
| notifications / ping | SDK | SDK-managed |
| unknown method/tool | SDK | JSON-RPC error |

## Error Behavior

`analyze_image()` never raises across the protocol boundary. Every failure is converted to a plain-text string inside the tool result, so agents see a description-like response rather than a structured error:

| Condition | Returned text |
|---|---|
| File does not exist | `Error: file not found at <path>` |
| Image smaller than 10×10 px | `Skipped: image too small (WxH) — likely corrupt or placeholder.` |
| Aspect ratio > 50:1 | `Skipped: extreme aspect ratio (WxH) — likely corrupt.` |
| File unreadable | `Error reading file: <e>` |
| HTTP error (non-2xx) | `HTTP error (code N): <preview>` — first 300 chars of the response body |
| API returned non-JSON | `API response parse error: <e>` |
| Network/API exception | `Error calling vision API: <e>` |

## Configuration Reference

Settings resolve with precedence **env var > config.json > default**. `config.json` lives in the repo directory next to `server.py`; it is gitignored.

| Config key | Env var | Default | Description |
|---|---|---|---|
| `vision_api_url` | `VISION_API_URL` | `http://localhost:8080/v1/chat/completions` | OpenAI-compatible chat completions endpoint |
| `vision_model` | `VISION_MODEL` | `OBSERVER` | Model label in the request body; any value works for single-model llama.cpp servers |
| `vision_max_tokens` | `VISION_MAX_TOKENS` | `2048` | Max response tokens |
| `vision_timeout` | `VISION_TIMEOUT` | `180` | Socket timeout for the urllib request, in seconds |

> **Note:** MCP clients spawn the server with a minimal environment allow-list, so env vars are not reliably inherited — prefer `config.json`.

Example `config.json`:

```json
{
  "vision_api_url": "http://localhost:8080/v1/chat/completions",
  "vision_model": "OBSERVER",
  "vision_max_tokens": 2048,
  "vision_timeout": 180
}
```

## Standalone CLI: `describe.sh`

Sends the same request without the MCP layer. Reads the same `config.json` (falls back to env vars / defaults when absent). It is a convenience for testing the model endpoint — the MCP server never invokes it.

```bash
./describe.sh /path/to/image.png
```

Prints the model's description to stdout. Exit code is non-zero if the file is missing.

## See Also

- [README](../README.md) — usage overview
- [architecture](architecture.md) — request flow and payload details
- [setup](setup.md) — install and verification
- [gotchas](gotchas.md) — behavior to watch out for
