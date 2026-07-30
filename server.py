#!/usr/bin/env python3
"""MCP server: local vision analysis via llama.cpp vision model.

Exposes the `vision_describe` tool — any agent (text-only or not) can
describe an image by passing its file path. The base64 encoding and API
call happen on this server side, so the calling model never needs vision
capabilities.
"""

import json
import sys
import base64
import struct
import subprocess
import os

# ── Config ──────────────────────────────────────────────────────────
# Point these at your llama.cpp server running a vision model
OBSERVER_URL = os.environ.get("VISION_API_URL",
                              "http://localhost:8080/v1/chat/completions")
VISION_MODEL = os.environ.get("VISION_MODEL", "OBSERVER")
MAX_TOKENS = int(os.environ.get("VISION_MAX_TOKENS", "800"))
TIMEOUT = int(os.environ.get("VISION_TIMEOUT", "180"))


# ── MCP transport helpers ──────────────────────────────────────────

def send(msg: dict):
    """Send a JSON-RPC message over stdout with MCP length prefix."""
    data = json.dumps(msg, ensure_ascii=False)
    header = struct.pack(">I", len(data))
    sys.stdout.buffer.write(header + data.encode("utf-8"))
    sys.stdout.buffer.flush()


def recv() -> dict | None:
    """Read a JSON-RPC message from stdin with MCP length prefix."""
    raw = sys.stdin.buffer.read(4)
    if not raw or len(raw) < 4:
        return None
    length = struct.unpack(">I", raw)[0]
    payload = sys.stdin.buffer.read(length)
    return json.loads(payload.decode("utf-8"))


# ── Vision API call ────────────────────────────────────────────────

def analyze_image(file_path: str, prompt: str = "Describe this image in detail.") -> str:
    """Base64-encode an image and send to the vision model API."""
    if not os.path.isfile(file_path):
        return f"Error: file not found at {file_path}"

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
        "max_tokens": MAX_TOKENS
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
        return data["choices"][0]["message"]["content"]
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
            "serverInfo": {"name": "mcp-local-vision", "version": "1.0.0"}
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
