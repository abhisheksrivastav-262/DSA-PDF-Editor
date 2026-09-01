#!/bin/bash
set -e
cd "$(dirname "$0")/backend"
PY="/opt/homebrew/bin/python3.12"
if [ ! -x "$PY" ]; then PY="python3"; fi
echo "Using Python: $($PY --version)"
$PY -m pip install -r requirements.txt --break-system-packages 2>&1 | tail -n 5
echo "Starting backend on http://127.0.0.1:8000 (docs at /docs)..."
$PY -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
