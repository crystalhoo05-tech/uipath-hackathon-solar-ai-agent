#!/usr/bin/env bash
# Test all example payloads against a running local server.
# Usage: ./examples/test_all.sh [base_url]

set -euo pipefail

BASE_URL="${1:-http://localhost:8080}"

echo "==> Health check"
curl -s "${BASE_URL}/health" | python3 -m json.tool
echo

for file in examples/0*.json; do
  name=$(basename "$file")
  echo "==> POST /api/v1/diagnostics/run  (${name})"
  curl -s -X POST "${BASE_URL}/api/v1/diagnostics/run" \
    -H "Content-Type: application/json" \
    -d @"${file}" | python3 -m json.tool
  echo
done

echo "==> POST /api/v1/diagnostics/chat"
curl -s -X POST "${BASE_URL}/api/v1/diagnostics/chat" \
  -H "Content-Type: application/json" \
  -d @examples/chat_followup.json | python3 -m json.tool
