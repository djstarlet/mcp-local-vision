# Install mcp-local-vision

Instructions for an AI agent.

## Required from user

The user must provide:
- **llama.cpp server URL** — e.g. `http://localhost:8080/v1/chat/completions`
- **Vision model name** — the model label for llama.cpp's API (any value works for single-model servers), e.g. `OBSERVER`
- **Clone path** — where to clone the repo (default: `~/projects/mcp-local-vision`)

If the user didn't include these, ask for them before proceeding.

## Steps

### 1. Clone the repo

```bash
git clone https://github.com/djstarlet/mcp-local-vision.git <clone-path>
```

### 2. Create config.json

Write `<clone-path>/config.json`:

```json
{
  "vision_api_url": "<server URL from user>",
  "vision_model": "<model name from user>",
  "vision_max_tokens": 2048,
  "vision_timeout": 180
}
```

### 3. Add to opencode.jsonc

Find the project's `opencode.jsonc` (or `.opencode.jsonc`) and add:

```jsonc
"mcp": {
  "local-vision": {
    "type": "local",
    "command": ["python3", "<clone-path>/server.py"],
    "enabled": true
  }
}
```
