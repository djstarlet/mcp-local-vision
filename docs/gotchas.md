---
title: MCP Local Vision Gotchas
date: 2026-08-05
tags: [mcp, vision, gotchas, troubleshooting]
---

# MCP Local Vision Gotchas

This document collects the pitfalls, sharp edges, and known issues of mcp-local-vision — things that are easy to trip over when setting it up, wiring it into clients, or extending the code. Each entry gives the symptom and the fix.

## Environment and Configuration

- **Symptom:** `VISION_API_URL` and the other env vars are set in your shell, but the server still talks to `localhost:8080`.
  **Fix:** MCP clients spawn server subprocesses with a minimal environment allow-list (PATH, HOME, etc.) — custom env vars are **not** reliably inherited. Put settings in `config.json`, which is always read from the server's own directory.

- **Symptom:** After cloning, the server points at `localhost:8080` instead of the real backend.
  **Fix:** `config.json` is gitignored — a fresh clone has no config and falls back to defaults. Copy `config.json.example` and set `vision_api_url`.

- **Symptom:** The server process exits immediately when the client starts it.
  **Fix:** The `mcp` package is missing — `server.py` prints `Error: the 'mcp' package is required but not installed.` to stderr and exits with code 1. Run `pip install mcp` in the Python environment the client uses to spawn the server.

## Image Handling

- **Symptom:** A valid JPEG is rejected or described oddly by a strict backend.
  **Fix:** The data URI is hardcoded to `data:image/png;base64,...` regardless of the actual format. llama.cpp tolerates it; other OpenAI-compatible backends may not.

- **Symptom:** A tiny but valid image (e.g. an 8×8 icon) is "skipped" instead of described.
  **Fix:** The pre-flight check rejects anything under 10×10 px (`MIN_DIM`) or with an aspect ratio over 50:1 (`MAX_RATIO`) as "likely corrupt". The message is returned as a normal tool result, so agents may report it as if the file were broken.

- **Symptom:** A reasoning model returns an empty description.
  **Fix:** With `reasoning_budget: 0` the model may put the answer in `reasoning_content` instead of `content`. The server falls back to `reasoning_content` whenever `content` is empty; if both are empty you get an empty string.

- **Symptom:** Very large images cause slow calls and high memory use.
  **Fix:** There is no size limit or downscaling — the whole file is base64-encoded in memory and POSTed in one request. Downscale or cap the file size before calling if this matters.

- **Symptom:** `describe.sh` returns `File not found` for valid paths with spaces or special characters.
  **Fix:** The script interpolates the path into inline Python without quoting. Quote the argument when calling from scripts. Note that `describe.sh` is a standalone convenience — the MCP server never invokes it, so fixing the script does not affect the MCP path.

## Platform-Specific

- **Symptom:** `pip install mcp` fails with "externally-managed-environment" on Linux (Ubuntu 23.04+, Debian 12+, Fedora).
  **Fix:** That is PEP 668 — install into a venv (`python3 -m venv .venv && .venv/bin/pip install mcp`) or use pipx, then point the registration command pair at the venv's python (e.g. `<clone-path>/.venv/bin/python <clone-path>/server.py`).

- **Symptom:** On macOS, running `python3` prompts to install Command Line Tools, or `pip` is missing.
  **Fix:** Install Python via Homebrew (`brew install python`) and use that interpreter for `pip install mcp` and the registration command pair.

- **Symptom:** `describe.sh: command not found` or "bash: No such file or directory" on Windows.
  **Fix:** The script is a bash convenience and not part of the MCP path — use the MCP client route instead, or run it under Git Bash / WSL.

## Clients and Deployment

- **Symptom:** The client fails to spawn the server on Windows ("command not found" / spawn error).
  **Fix:** Use `python` (or `py -3`) as the command, not `python3`, which usually does not exist on Windows. Install Python from python.org if `python` is missing.

- **Symptom:** Errors look like normal tool output, so agents may "describe" an error string.
  **Fix:** All failures are returned as plain text in the tool result, never as protocol errors. Treat the `Error:` / `Skipped:` / `HTTP error` prefixes as failures when reading results.

- **Symptom:** `Error calling vision API: <urlopen error ... Connection refused ...>`.
  **Fix:** The llama.cpp backend is not running, or `vision_api_url` points at the wrong host/port. Verify with `./describe.sh <image>`; also confirm the backend was started with `--mmproj` (without the projector, image requests fail at the API level).

- **Symptom:** `API response parse error` with no raw preview.
  **Fix:** The backend returned non-JSON. Check `vision_api_url` for a typo and that the endpoint ends with `/v1/chat/completions`. The old raw-response preview was dropped with the urllib port.

- **Symptom:** `start.sh` fails on a different machine.
  **Fix:** It hardcodes `/usr/bin/python3` and `/home/youruser/projects/mcp-local-vision/server.py`. Register `python3 <path>/server.py` in the client instead of using this wrapper.

- **Symptom:** Concern that upgrading `mcp` to 2.x will break the server.
  **Fix:** The import shim accepts both mcp 1.x (`FastMCP`) and 2.x (`MCPServer`). Don't pin a version — `pip install mcp` is the documented install.

## See Also

- [README](../README.md) — what the server does
- [api](api.md) — reference tables for tools and config
- [setup](setup.md) — installation and verification steps
