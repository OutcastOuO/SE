#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_command curl

echo "Checking VMS API at ${BASE_URL}"

health="$(curl -fsS "${BASE_URL}/health")"
echo "Health: ${health}"

chaos_health="$(curl -fsS "${BASE_URL}/api/chaos/health")"
echo "Chaos health: ${chaos_health}"

vehicles="$(curl -fsS "${BASE_URL}/api/vehicles")"
echo "Vehicle API bytes: ${#vehicles}"

metrics="$(curl -fsS "${BASE_URL}/metrics")"
if [[ "${metrics}" != *"vms_http_requests_total"* ]]; then
  echo "Metrics endpoint did not expose vms_http_requests_total" >&2
  exit 1
fi

echo "Metrics endpoint OK"
echo "Smoke test passed"
