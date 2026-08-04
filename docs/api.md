---
title: MCP Local Vision API Reference
date: 2026-08-05
tags: [mcp, vision, api, reference]
---

# MCP Local Vision API Reference

This document is the reference for the public surface of mcp-local-vision: the MCP tool it exposes, the JSON-RPC methods it answers, and every configuration option. Use it when wiring the server into a client, writing agent prompts, or tuning behavior.

The server exposes exactly one tool, `vision_describe`, and a hand-rolled subset of the MCP lifecycle over stdio.

## Server Identity

| Property | Value |
|---|---|
| Name | `local-vision` |
| Version | `1.0.0` |
| Protocol version | `2024-11-05` |
| Transport | newline-delimited JSON over stdio |
| Capabilities | `tools` only |

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
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [{"type": "text", "text": "The image shows... "}]
  }
}
```

## MCP Methods

| Method | Request | Response |
|---|---|---|
| `initialize` | any first message | Server info: protocol `2024-11-05`, `serverInfo` `local-vision` v1.0.0 |
| `tools/list` | — | List containing the `vision_describe` tool |
| `tools/call` | `name: "vision_describe"`, `arguments: {file_path, prompt?}` | Text content with the description |
| `shutdown` | — | `result: null`, then process exits |
| notification (no `id`) | any | Silently ignored |
| unknown method/tool | — | Error `-32601` `Unknown method: <m>` / `Unknown tool: <t>` |

> **Note:** `main()` treats the *first* message as `initialize` unconditionally. If a client's first message is something else, the reply is still the init result; the real request is processed on the next message.

## Error Behavior

`analyze_image()` never raises across the protocol boundary. Every failure is converted to a plain-text string inside the tool result, so agents see a description-like response rather than a structured error:

| Condition | Returned text |
|---|---|
| File does not exist | `Error: file not found at <path>` |
| Image smaller than 10×10 px | `Skipped: image too small (WxH) — likely corrupt or placeholder.` |
| Aspect ratio > 50:1 | `Skipped: extreme aspect ratio (WxH) — likely corrupt.` |
| File unreadable | `Error reading file: <e>` |
| `curl` failed | `curl error (code <n>): <stderr>` |
| API returned non-JSON | `API response parse error: <e>` + raw preview |
| Network/API exception | `Error calling vision API: <e>` |

## Configuration Reference

Settings resolve with precedence **env var > config.json > default**. `config.json` lives in the repo directory next to `server.py`; it is gitignored.

| Config key | Env var | Default | Description |
|---|---|---|---|
| `vision_api_url` | `VISION_API_URL` | `http://localhost:8080/v1/chat/completions` | OpenAI-compatible chat completions endpoint |
| `vision_model` | `VISION_MODEL` | `OBSERVER` | Model label in the request body; any value works for single-model llama.cpp servers |
| `vision_max_tokens` | `VISION_MAX_TOKENS` | `2048` | Max response tokens |
| `vision_timeout` | `VISION_TIMEOUT` | `180` | `curl --max-time` in seconds; subprocess timeout is this + 20 s |

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

Sends the same request without the MCP layer. Reads the same `config.json` (falls back to env vars / defaults when absent).

```bash
./describe.sh /path/to/image.png
```

Prints the model's description to stdout. Exit code is non-zero if the file is missing.

## See Also

- [README](../README.md) — usage overview
- [architecture](architecture.md) — request flow and payload details
- [setup](setup.md) — install and verification
- [gotchas](gotchas.md) — behavior to watch out for
