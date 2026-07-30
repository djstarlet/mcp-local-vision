#!/bin/bash
# describe.sh — describe an image using the local OBSERVER vision model
# Usage: describe.sh <image-file-path>

set -e
FP="$1"
if [ -z "$FP" ]; then echo "Usage: describe.sh <filepath>" >&2; exit 1; fi
if [ ! -f "$FP" ]; then echo "File not found: $FP" >&2; exit 1; fi

DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="$DIR/config.json"

if [ -f "$CONFIG" ]; then
  URL=$(python3 -c "import json; print(json.load(open('$CONFIG')).get('vision_api_url','http://localhost:8080/v1/chat/completions'))")
  TOKENS=$(python3 -c "import json; print(json.load(open('$CONFIG')).get('vision_max_tokens',2048))")
  MODEL=$(python3 -c "import json; print(json.load(open('$CONFIG')).get('vision_model','OBSERVER'))")
else
  URL="${VISION_API_URL:-http://localhost:8080/v1/chat/completions}"
  TOKENS="${VISION_MAX_TOKENS:-2048}"
  MODEL="${VISION_MODEL:-OBSERVER}"
fi

python3 -c "
import base64, json, subprocess, os, sys
fp = '$FP'
url = '$URL'
tokens = $TOKENS
model = '$MODEL'
b64 = base64.b64encode(open(fp, 'rb').read()).decode()
pl = json.dumps({'model': model, 'messages': [{'role': 'user', 'content': [{'type': 'text', 'text': 'Describe this image in detail.'}, {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + b64}}]}], 'max_tokens': tokens, 'reasoning_budget': 0})
with open('/tmp/vis.json', 'w') as f: f.write(pl)
r = subprocess.run(['curl', '-s', '--max-time', '180', url, '-H', 'Content-Type: application/json', '-d@/tmp/vis.json'], capture_output=True, text=True)
os.remove('/tmp/vis.json')
d = json.loads(r.stdout)
msg = d['choices'][0]['message']
content = msg.get('content', '') or msg.get('reasoning_content', '')
sys.stdout.write(content)
"