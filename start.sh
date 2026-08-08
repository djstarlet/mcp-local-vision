#!/bin/bash
# start.sh — run the MCP server directly on stdio (for manual testing)
DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$DIR/server.py"
