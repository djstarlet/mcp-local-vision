# mcp-local-vision

A minimal MCP server that lets any text-only AI agent describe local images by
calling a local llama.cpp vision model (tested with Qwen 3.5 4B, also works
with MiniCPM-V, LLaVA, etc.) through its OpenAI-compatible API.

No special model configuration is needed. Agents just call
`vision_describe("path.png")` and get back a text description from the vision
model.

## Why this exists

Text-only agents cannot see images. The usual workaround, uploading files to
a cloud vision API, is a privacy and latency problem when the images live on
the same machine. mcp-local-vision is a ~150-line MCP server that exposes a
locally run vision model as a standard MCP tool, so any agent in any MCP
client can describe local images without anything leaving the machine.

## Features

- **One tool, one dependency.** The server exposes a single tool,
  `vision_describe(file_path, prompt?)`, and needs only `pip install mcp`.
- **Any MCP client.** Standard MCP stdio transport: opencode, Claude Code, Codex,
  VS Code, Cline, Cursor, Zed, and others.
- **Zero image dependencies.** PNG/JPEG dimensions are read straight from the
  file headers and the image is base64-encoded with the stdlib. No PIL, no
  native packages.
- **mcp 1.x and 2.x compatible.** An import shim accepts both SDK lines, so
  no version pin is needed.
- **Backend-agnostic.** Talks to any OpenAI-compatible vision endpoint;
  tested with llama.cpp, and other servers work unchanged.
- **Errors agents can read.** Every failure is returned as plain text in the
  tool result, never a protocol error, so the agent can report what went wrong.
- **CLI helper.** `describe.sh` exercises the model endpoint without the MCP
  layer, handy for debugging.

## Quick start

Requirements: Python 3.10+ on any OS (Linux, macOS, Windows), and a running
llama.cpp server with a vision model (see step 3).

1. Clone, install, and copy the config template:

   ```bash
   git clone https://github.com/djstarlet/mcp-local-vision.git
   cd mcp-local-vision
   pip install mcp
   cp config.json.example config.json
   ```

2. Point `config.json` at your model server (see
   [Configuration](#configuration) for all options):

   ```json
   {
     "vision_api_url": "http://localhost:8080/v1/chat/completions",
     "vision_model": "OBSERVER",
     "vision_max_tokens": 2048,
     "vision_timeout": 180
   }
   ```

3. Have llama.cpp running with the model and its vision projector
   (`--mmproj` is required for image input):

   ```bash
   ./llama-server -m model.gguf --mmproj mmproj.gguf \
     --host 0.0.0.0 --port 8080
   ```

4. Register the server with your MCP client. Every MCP client registers a
   stdio server as a `command` + `args` pair. For this project, the pair is
   always:

   ```text
   python3 /path/to/mcp-local-vision/server.py
   ```

   | Client | Registration |
   |---|---|
   | opencode | In `opencode.jsonc`: `"mcp": { "local-vision": { "type": "local", "command": ["python3", "/path/to/mcp-local-vision/server.py"], "enabled": true } }` |
   | Claude Code | `claude mcp add local-vision -- python3 /path/to/mcp-local-vision/server.py` |
   | Codex | `codex mcp add local-vision -- python3 /path/to/mcp-local-vision/server.py` |
   | VS Code | In `.vscode/mcp.json`: `{"servers": {"local-vision": {"type": "stdio", "command": "python3", "args": ["/path/to/mcp-local-vision/server.py"]}}}` |
   | All other clients | Their MCP settings UI or config file, using the same `command` + `args` pair (Cline, Cursor, Zed, ...) |

5. Restart the client, then ask any agent to call
   `vision_describe("/path/to/image.png")` and confirm a description comes
   back.

> **Note:** on Windows, use `python` (or the full path to `python.exe`) instead
> of `python3` in the commands above.

> **Platform notes:**
> - **Windows:** install Python from [python.org](https://www.python.org/downloads/).
> - **macOS:** install Python via Homebrew (`brew install python`); the system `python3` may be a Command Line Tools stub or lack pip.
> - **Linux:** on distros with PEP 668 (Ubuntu 23.04+, Debian 12+, Fedora) `pip install` fails with "externally-managed-environment"; use a venv (`python3 -m venv .venv && .venv/bin/pip install mcp`) or pipx, and point the registration pair at the venv's python.

## Install via your AI agent

Tell your AI agent:

```
Install and configure mcp-local-vision -
https://github.com/djstarlet/mcp-local-vision/blob/main/INSTALL.md
```

The agent will fetch [INSTALL.md](INSTALL.md) and walk through the steps.
You'll need to provide your server URL and model alias when asked.

## How it works

The server is a single Python file (`server.py`, ~150 lines) built on the
official MCP Python SDK with standard stdio framing, so it works in any MCP
client without network configuration.

- **Transport.** The SDK runs the MCP stdio server: the `initialize`
  handshake, `tools/list`, `tools/call`, and `shutdown`. `server.py` only
  registers one tool via `@mcp.tool()` and calls `mcp.run()`.
- **Tool schema.** `vision_describe(file_path: string, prompt?: string)`.
  `file_path` is required (absolute path to a PNG/JPG); `prompt` defaults to
  `Describe this image in detail.`
- **Request flow.** On a call, the server validates the file, reads its
  dimensions from the PNG/JPEG headers (rejecting corrupt-looking images under
  10×10 px or with an extreme aspect ratio), base64-encodes it, and POSTs an
  OpenAI-format chat-completions payload (`image_url` with a data URI) to the
  model endpoint via stdlib `urllib`.
- **Response.** The model's text is returned as the tool result; for
  reasoning models the server falls back to `reasoning_content` when `content`
  is empty. Failures are returned as plain-text error strings.

See [docs/architecture.md](docs/architecture.md) for the full data flow and
transport details.

## Tech stack and why

| Decision | Why |
|---|---|
| Official `mcp` Python SDK, stdio transport | Standard MCP framing, interoperable with every MCP client, no custom protocol code |
| stdlib `urllib` instead of `requests` | Zero Python dependencies beyond the `mcp` package itself |
| No PIL / no image libraries | PNG/JPEG dimensions come from a small header parser, which keeps the server a single dependency-light file |
| `config.json` beside `server.py`, env vars as overrides | MCP clients spawn subprocesses with a minimal environment allow-list, so env vars are not reliably inherited; `config.json` is always readable from the server's own directory |
| mcp 1.x/2.x import shim | `FastMCP` was renamed `MCPServer` in mcp 2.0; the shim accepts either, so `pip install mcp` works today and after upgrades |
| OpenAI-compatible chat-completions payload with base64 data URI | The de-facto standard vision format; works with llama.cpp and other OpenAI-compatible servers unchanged |

## Configuration

All values can be set in `config.json` (copy `config.json.example`) or
overridden per-process via environment variables:

| Config key | Env var | Default | Description |
|---|---|---|---|
| `vision_api_url` | `VISION_API_URL` | `http://localhost:8080/v1/chat/completions` | OpenAI-compatible endpoint |
| `vision_model` | `VISION_MODEL` | `OBSERVER` | Model label (any value works for single-model servers) |
| `vision_max_tokens` | `VISION_MAX_TOKENS` | `2048` | Max response tokens |
| `vision_timeout` | `VISION_TIMEOUT` | `180` | API timeout in seconds |

> **Note:** prefer `config.json` over environment variables. MCP clients spawn
> the server as a subprocess with a minimal environment allow-list (PATH, HOME,
> etc.), so custom variables like `VISION_API_URL` are not reliably inherited.
> `config.json` is always read from the server's own directory.

`vision_model` is just a label passed to the OpenAI-compatible API. If you run
a single model directly with `llama-server`, any value works. Set it to
`"model"`, `"OBSERVER"`, or whatever you like.

## Subagent access

Subagents (e.g. `@vision`, `@observer`) need the `mcp` tool group to use MCP
tools. Add it to their config in `opencode.jsonc` or your agent preset:

```jsonc
"<subagent-name>": {
  "model": "...",
  "toolGroups": ["mcp", "read"]  // <-- "mcp" grants MCP tool access
}
```

This lets the subagent call `vision_describe` via any configured MCP server.

## Known limitations

- **No image downscaling.** The whole file is base64-encoded in memory and
  sent in one request; very large images mean slow calls and high memory use.
- **Hardcoded MIME type.** The data URI is always `data:image/png;base64,...`
  even for JPEG input; llama.cpp tolerates this, stricter backends may not.
- **Single tool.** One image per call, no streaming, no multi-image batches.
- **`describe.sh` quoting.** Paths containing spaces must be quoted; the
  script interpolates the path into inline Python.

## What I'd do next

- Downscale or cap image size before encoding (stdlib-only resizing is not
  practical; a Pillow-optional path would do).
- Send the correct MIME type per image format.
- Add optional streaming responses and multi-image input.
- Make the pre-flight thresholds (`MIN_DIM`, `MAX_RATIO`) configurable.

## License

MIT. See [LICENSE](LICENSE).

## Documentation

- [INSTALL.md](INSTALL.md): agent-driven install instructions
- [docs/setup.md](docs/setup.md): manual setup and verification
- [docs/api.md](docs/api.md): API and configuration reference
- [docs/architecture.md](docs/architecture.md): internals and data flow
- [docs/gotchas.md](docs/gotchas.md): known pitfalls and fixes
