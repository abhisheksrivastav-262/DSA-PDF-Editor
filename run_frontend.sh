#!/bin/bash
set -e
cd "$(dirname "$0")/frontend"
echo "Node: $(node --version)  NPM: $(npm --version)"
npm install
echo "Starting frontend on http://127.0.0.1:3000 (proxies /api -> 8000)..."
npm run dev
