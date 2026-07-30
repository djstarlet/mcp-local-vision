# Agent-assisted installation

Copy the following prompt to have your AI coding agent install
mcp-local-vision in any project.

> You need to provide your model path (GGUF + mmproj files) since
> the agent cannot know your local file layout.

---

## Prompt template

```
Install mcp-local-vision into this project from
https://github.com/djstarlet/mcp-local-vision

Steps:
1. Clone the repo into a local directory (e.g. ~/projects/mcp-local-vision)
2. Create config.json in that directory with:
   - vision_api_url: the URL of my llama.cpp server running a vision model
   - vision_model: the model alias from my modelfile.ini (e.g. OBSERVER)
3. Add the MCP server config to opencode.jsonc:
   "mcp": {
     "local-vision": {
       "type": "local",
       "command": ["python3", "/path/to/mcp-local-vision/server.py"],
       "enabled": true
     }
   }
4. Confirm the llama.cpp server is running with --host 0.0.0.0 --port 8080
```

### You must tell the agent

| What | Example |
|------|---------|
| llama.cpp server URL | `http://my-server:8080/v1/chat/completions` |
| Vision model alias | `OBSERVER` |
| Local clone path | `/home/me/projects/mcp-local-vision` |

---

## Manual install

```bash
# clone
git clone https://github.com/djstarlet/mcp-local-vision.git ~/projects/mcp-local-vision

# configure
cp ~/projects/mcp-local-vision/config.json.example \
   ~/projects/mcp-local-vision/config.json
# edit config.json with your server URL and model name

# add to opencode.jsonc:
# "mcp": { "local-vision": { "type": "local",
#   "command": ["python3", "/path/to/mcp-local-vision/server.py"],
#   "enabled": true } }
```
