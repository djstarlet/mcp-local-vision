# mcp-local-vision

MCP server that lets any text-only agent describe images by calling a local
llama.cpp vision model (MiniCPM-V, LLaVA, etc.) through its OpenAI-compatible
API.

No special model config needed — agents just call `vision_describe("path.png")`
and get back a text description from the vision model.

## Tools

| Tool | Description |
|------|-------------|
| `vision_describe(file_path, prompt?)` | Describe an image via the local vision model |

## Setup

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

## Config via environment

| Variable | Default | Description |
|----------|---------|-------------|
| `VISION_API_URL` | `http://localhost:8080/v1/chat/completions` | OpenAI-compatible endpoint |
| `VISION_MODEL` | `OBSERVER` | Model name on the server |
| `VISION_MAX_TOKENS` | `800` | Max response tokens |
| `VISION_TIMEOUT` | `180` | API timeout in seconds |
