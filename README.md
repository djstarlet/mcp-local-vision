# mcp-local-vision

MCP server that lets any text-only agent describe images by calling a local
llama.cpp vision model (tested with Qwen 3.5 4B, also works with MiniCPM-V,
LLaVA, etc.) through its OpenAI-compatible API.

No special model config needed — agents just call `vision_describe("path.png")`
and get back a text description from the vision model.

## Install via your AI agent

Tell your AI agent:

```
Install and configure mcp-local-vision -
https://github.com/djstarlet/mcp-local-vision/src/branch/main/INSTALL.md
```

The agent will fetch INSTALL.md and walk through the steps. You'll need to
provide your server URL and model alias when asked.

## Setup (manual)

1. Have a llama.cpp server running with a vision model (e.g. MiniCPM-V 4.6):

   ```
   ./llama-server -m model.gguf --mmproj mmproj.gguf \
     --host 0.0.0.0 --port 8080
   ```

2. Add to your `opencode.jsonc`:

   ```jsonc
   "mcp": {
     "local-vision": {
       "type": "local",
       "command": ["python3", "/path/to/mcp-local-vision/server.py"],
       "enabled": true
     }
   }
   ```

3. Restart opencode. Now any agent can call `vision_describe`.

## Subagent access

Subagents (e.g. `@vision`, `@observer`) need the `mcp` tool group to use
MCP tools. Add it to their config in `opencode.jsonc` or your agent preset:

```jsonc
"<subagent-name>": {
  "model": "...",
  "toolGroups": ["mcp", "read"]  // <-- "mcp" grants MCP tool access
}
```

This lets the subagent call `vision_describe` via any configured MCP server.

## Configuration

Create `config.json` in this directory (copy `config.json.example`):

```json
{
  "vision_api_url": "http://your-server:8080/v1/chat/completions",
  "vision_model": "OBSERVER",
  "vision_max_tokens": 2048,
  "vision_timeout": 180
}
```

`vision_model` is just a label passed to the OpenAI-compatible API. If you
run a single model directly with `llama-server`, any value works — set it to
`"model"`, `"OBSERVER"`, or whatever you like.

All values can also be overridden via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_API_URL` | `http://localhost:8080/v1/chat/completions` | OpenAI-compatible endpoint |
| `VISION_MODEL` | `OBSERVER` | Model label (any value works for single-model servers) |
| `VISION_MAX_TOKENS` | `2048` | Max response tokens |
| `VISION_TIMEOUT` | `180` | API timeout in seconds |
