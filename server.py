#!/usr/bin/env python3
"""MCP server: local vision analysis via llama.cpp vision model."""

import json
import sys
import base64
import struct
import subprocess
import os

# ── Config ──────────────────────────────────────────────────────────
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

_config = {}
if os.path.isfile(CONFIG_PATH):
    with open(CONFIG_PATH) as f:
        _config = json.load(f)

OBSERVER_URL = os.environ.get("VISION_API_URL") or _config.get("vision_api_url",
                               "http://localhost:8080/v1/chat/completions")
VISION_MODEL = os.environ.get("VISION_MODEL") or _config.get("vision_model", "OBSERVER")
MAX_TOKENS = int(os.environ.get("VISION_MAX_TOKENS") or _config.get("vision_max_tokens", "2048"))
TIMEOUT = int(os.environ.get("VISION_TIMEOUT") or _config.get("vision_timeout", "180"))


# ── MCP transport helpers ──────────────────────────────────────────
# opencode uses newline-delimited JSON on stdio (NOT the 4-byte length-prefix format)

def send(msg: dict):
    """Send a JSON-RPC message line to stdout."""
    data = json.dumps(msg, ensure_ascii=False)
    sys.stdout.write(data + "\n")
    sys.stdout.flush()


def recv() -> dict | None:
    """Read a JSON-RPC message line from stdin."""
    line = sys.stdin.readline()
    if not line:
        return None
    return json.loads(line.strip())


# ── Vision API call ────────────────────────────────────────────────

MIN_DIM = 10
MAX_RATIO = 50

def _image_dims(path: str) -> tuple[int, int] | None:
    """Quick-read PNG or JPEG dimensions without PIL."""
    try:
        with open(path, "rb") as f:
            h = f.read(32)
        if h[:8] == b'\x89PNG\r\n\x1a\n':
            w, h = struct.unpack('>II', h[16:24])
            return w, h
        if h[:2] in (b'\xff\xd8',):
            f = open(path, "rb")
            f.read(2)
            while True:
                b = f.read(1)
                if not b or b[0] != 0xff:
                    break
                b = f.read(1)
                m = b[0]
                if m == 0xc0 or m == 0xc1 or m == 0xc2:
                    f.read(3)
                    h, w = struct.unpack('>HH', f.read(4))
                    return w, h
                l = struct.unpack('>H', f.read(2))[0]
                f.read(l - 2)
            f.close()
            return None
        return None
    except Exception:
        return None

def analyze_image(file_path: str, prompt: str = "Describe this image in detail.") -> str:
    """Base64-encode an image and send to the vision model API."""
    if not os.path.isfile(file_path):
        return f"Error: file not found at {file_path}"

    dims = _image_dims(file_path)
    if dims:
        w, h = dims
        if w < MIN_DIM or h < MIN_DIM:
            return f"Skipped: image too small ({w}x{h}) — likely corrupt or placeholder."
        if w / h > MAX_RATIO or h / w > MAX_RATIO:
            return f"Skipped: extreme aspect ratio ({w}x{h}) — likely corrupt."

    try:
        with open(file_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
    except Exception as e:
        return f"Error reading file: {e}"

    payload = json.dumps({
        "model": VISION_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/png;base64,{b64}"
                }}
            ]
        }],
        "max_tokens": MAX_TOKENS,
        "reasoning_budget": 0
    })

    try:
        # Write to temp file to avoid "argument list too long" on large base64
        tmp = "/tmp/mcp-vision-payload.json"
        with open(tmp, "w") as f:
            f.write(payload)
        r = subprocess.run(
            ["curl", "-s", "--max-time", str(TIMEOUT),
             OBSERVER_URL,
             "-H", "Content-Type: application/json",
             "-d", f"@{tmp}"],
            capture_output=True, text=True, timeout=TIMEOUT + 20
        )
        if r.returncode != 0:
            return f"curl error (code {r.returncode}): {r.stderr[:200]}"
        data = json.loads(r.stdout)
        msg = data["choices"][0]["message"]
        content = msg.get("content", "")
        if not content:
            content = msg.get("reasoning_content", "")
        return content
    except json.JSONDecodeError as e:
        preview = r.stdout[:300] if 'r' in dir() else "N/A"
        return f"API response parse error: {e}\nRaw: {preview}"
    except Exception as e:
        return f"Error calling vision API: {e}"


# ── MCP server loop ────────────────────────────────────────────────

def main():
    msg = recv()
    if msg is None:
        return

    # Respond to initialize
    init_result = {
        "jsonrpc": "2.0",
        "id": msg.get("id", 0),
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "local-vision", "version": "1.0.0"}
        }
    }
    send(init_result)

    while True:
        msg = recv()
        if msg is None:
            break
        method = msg.get("method")
        msg_id = msg.get("id")
        params = msg.get("params", {})

        if msg_id is None:  # notification
            continue

        if method == "tools/list":
            send({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": [
                        {
                            "name": "vision_describe",
                            "description": "Analyze an image using the local vision model. Returns a detailed description of the image contents.",
                            "inputSchema": {
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
                        }
                    ]
                }
            })

        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})

            if tool_name == "vision_describe":
                file_path = args.get("file_path", "")
                prompt = args.get("prompt", "Describe this image in detail.")
                result = analyze_image(file_path, prompt)
                send({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": result}]
                    }
                })
            else:
                send({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
                })

        elif method == "shutdown":
            send({"jsonrpc": "2.0", "id": msg_id, "result": None})
            break

        else:
            send({
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Unknown method: {method}"}
            })


if __name__ == "__main__":
    main()
