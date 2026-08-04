#!/usr/bin/env python3
"""MCP server: local vision analysis via llama.cpp vision model."""

import json
import sys
import base64
import struct
import os
import urllib.request
import urllib.error

# ── Dependency check ───────────────────────────────────────────────
# Works with mcp 1.x (FastMCP) and mcp 2.x (MCPServer — FastMCP was renamed).
try:
    from mcp.server import MCPServer  # mcp >= 2.0
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP as MCPServer  # mcp 1.x
    except ImportError:
        print("Error: the 'mcp' package is required but not installed.", file=sys.stderr)
        print("Install it with: pip install mcp", file=sys.stderr)
        sys.exit(1)


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


# ── Image dimension parser (dependency-free) ───────────────────────

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


# ── Vision API call ────────────────────────────────────────────────

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
    }).encode("utf-8")

    try:
        request = urllib.request.Request(
            OBSERVER_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=TIMEOUT) as resp:
            body = resp.read()
        data = json.loads(body)
        msg = data["choices"][0]["message"]
        content = msg.get("content", "")
        if not content:
            content = msg.get("reasoning_content", "")
        return content
    except urllib.error.HTTPError as e:
        preview = e.read().decode("utf-8", errors="replace")[:300]
        return f"HTTP error (code {e.code}): {preview}"
    except json.JSONDecodeError as e:
        return f"API response parse error: {e}"
    except Exception as e:
        return f"Error calling vision API: {e}"


# ── MCP server ─────────────────────────────────────────────────────

mcp = MCPServer("local-vision")


@mcp.tool()
def vision_describe(file_path: str, prompt: str = "Describe this image in detail.") -> str:
    """Analyze an image using the local vision model. Returns a detailed description of the image contents."""
    return analyze_image(file_path, prompt)


if __name__ == "__main__":
    mcp.run()
