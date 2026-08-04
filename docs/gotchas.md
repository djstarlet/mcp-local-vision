---
title: MCP Local Vision Gotchas
date: 2026-08-05
tags: [mcp, vision, gotchas, troubleshooting]
---

# MCP Local Vision Gotchas

This document collects the pitfalls, sharp edges, and known issues of mcp-local-vision — things that are easy to trip over when setting it up, wiring it into clients, or extending the code. Each entry gives the symptom and the fix.

## Transport and Protocol

- **Symptom:** A client using the official MCP SDKs (Python/TypeScript) gets garbage or hangs; opencode works fine.
  **Fix:** The server speaks newline-delimited JSON, not the SDK's 4-byte length-prefixed framing. Only use clients that expect NDJSON on stdio (opencode does). Wrapping with the SDK requires rewriting `send`/`recv`.

- **Symptom:** A client whose first message is not `initialize` (e.g. it starts with `tools/list` or a ping) receives a wrong reply.
  **Fix:** `main()` assumes message #1 is always `initialize` and answers it unconditionally. Make the client send `initialize` first; the real request is processed on the next message.

- **Symptom:** Notifications seem to be dropped.
  **Fix:** That is by design — messages without an `id` are ignored (`continue`). The server implements no `notifications/initialized` or ping handling.

- **Symptom:** Errors look like normal tool output, so agents may "describe" an error string.
  **Fix:** All failures are returned as plain text in the tool result, never as JSON-RPC errors. If you need structured errors, patch `analyze_image`/`main` to emit error codes.

## Concurrency and Temp Files

- **Symptom:** Two `vision_describe` calls in parallel return each other's results or corrupted payloads.
  **Fix:** The payload is always written to the fixed path `/tmp/mcp-vision-payload.json` and the server never cleans it up (only `describe.sh` does). Concurrent calls clobber each other; the server is effectively single-flight. Use a unique temp path per call (e.g. `tempfile.NamedTemporaryFile`).

- **Symptom:** `/tmp/mcp-vision-payload.json` accumulates stale files.
  **Fix:** Expected behavior — the file is gitignored but not removed by `server.py`. Delete it manually or patch the server to `os.remove` after the curl call.

## Image Handling

- **Symptom:** A valid JPEG is rejected or described oddly by a strict backend.
  **Fix:** The data URI is hardcoded to `data:image/png;base64,...` regardless of the actual format. llama.cpp tolerates it; other OpenAI-compatible backends may not. Detect the mime type from the file extension or magic bytes.

- **Symptom:** Very large images cause slow calls and high memory use.
  **Fix:** There is no size limit or downscaling — the whole file is base64-encoded into memory and the payload written to disk. Downscale or cap file size before calling if this matters.

- **Symptom:** `describe.sh` returns `File not found` for valid paths with spaces or special characters.
  **Fix:** The script interpolates the path into inline Python without quoting. Quote the argument or pass it via an environment variable when calling from scripts.

## Deployment

- **Symptom:** After cloning, the server points at `localhost:8080` instead of the real backend.
  **Fix:** `config.json` is gitignored — a fresh clone has no config and falls back to defaults. Copy `config.json.example` and set `vision_api_url`.

- **Symptom:** `start.sh` fails on a different machine.
  **Fix:** It hardcodes `/usr/bin/python3` and `/home/youruser/projects/mcp-local-vision/server.py`. Use the `python3 server.py` command from opencode's MCP config instead of this wrapper.

- **Symptom:** `curl error (code 7)` — connection refused.
  **Fix:** The llama.cpp backend is not running, or `vision_api_url` points at the wrong host/port. Verify with `./describe.sh <image>`; also confirm the backend was started with `--mmproj` (without the projector, image requests fail at the API level).

- **Symptom:** `API response parse error` with a long raw preview.
  **Fix:** The backend returned non-JSON (proxy page, error HTML). Check `vision_api_url` for a typo, and that the endpoint ends with `/v1/chat/completions`.

## See Also

- [README](../README.md) — what the server does
- [api](api.md) — reference tables for tools and config
- [setup](setup.md) — installation and verification steps
