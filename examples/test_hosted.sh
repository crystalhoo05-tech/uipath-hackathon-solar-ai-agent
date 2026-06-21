#!/usr/bin/env bash
# Test the hosted Cloud Run API (requires gcloud auth).
# Usage: ./examples/test_hosted.sh [cloud-run-url]

set -euo pipefail

API_URL="${1:-https://solar-diagnostic-api-yguvvsuspa-uc.a.run.app}"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud CLI is required. Install: https://cloud.google.com/sdk/docs/install"
  exit 1
fi

echo "API URL: ${API_URL}"
echo "Getting identity token..."
TOKEN="$(gcloud auth print-identity-token)"

auth_header() {
  curl -s -H "Authorization: Bearer ${TOKEN}" "$@"
}

echo ""
echo "=== 1. Health (no auth) ==="
HTTP_NO_AUTH=$(curl -s -o /tmp/health_no_auth.json -w "%{http_code}" "${API_URL}/health")
echo "HTTP ${HTTP_NO_AUTH}"
cat /tmp/health_no_auth.json
echo ""

echo "=== 2. Health (with auth) ==="
HTTP_HEALTH=$(auth_header -o /tmp/health.json -w "%{http_code}" "${API_URL}/health")
echo "HTTP ${HTTP_HEALTH}"
python3 -m json.tool /tmp/health.json 2>/dev/null || cat /tmp/health.json
echo ""

echo "=== 3. Diagnostic run (with auth) ==="
HTTP_DIAG=$(auth_header -o /tmp/diag.json -w "%{http_code}" \
  -X POST "${API_URL}/api/v1/diagnostics/run" \
  -H "Content-Type: application/json" \
  -d @"${PROJECT_ROOT}/examples/03_string_fault_fail.json")
echo "HTTP ${HTTP_DIAG}"
python3 -m json.tool /tmp/diag.json 2>/dev/null | head -50 || cat /tmp/diag.json
echo ""

if [[ "${HTTP_NO_AUTH}" == "403" ]]; then
  echo "NOTE: Public access is disabled. UiPath will need auth OR run:"
  echo "  gcloud run services add-iam-policy-binding solar-diagnostic-api \\"
  echo "    --region=us-central1 --member=allUsers --role=roles/run.invoker"
fi

if grep -q "gemini_api_error" /tmp/diag.json 2>/dev/null; then
  echo ""
  echo "NOTE: Gemini model error on Cloud Run. Update model with:"
  echo "  gcloud run services update solar-diagnostic-api --region=us-central1 \\"
  echo "    --update-env-vars=GEMINI_MODEL=gemini-2.5-flash"
  echo "Or enable demo mode temporarily:"
  echo "  gcloud run services update solar-diagnostic-api --region=us-central1 \\"
  echo "    --update-env-vars=DEMO_MODE=true"
fi
