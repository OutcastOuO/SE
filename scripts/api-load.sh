#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
SECONDS_TO_RUN="${1:-90}"
DELAY_SECONDS="${DELAY_SECONDS:-0.3}"
END_AT=$((SECONDS + SECONDS_TO_RUN))
OK=0
FAIL=0

if ! command -v curl >/dev/null 2>&1; then
  echo "Missing required command: curl" >&2
  exit 1
fi

echo "Sending API traffic to ${BASE_URL} for ${SECONDS_TO_RUN} seconds..."

while (( SECONDS < END_AT )); do
  if curl -fsS "${BASE_URL}/api/vehicles" >/dev/null; then
    OK=$((OK + 1))
  else
    FAIL=$((FAIL + 1))
    echo "Request failed: /api/vehicles"
  fi

  if curl -fsS "${BASE_URL}/api/chaos/health" >/dev/null; then
    OK=$((OK + 1))
  else
    FAIL=$((FAIL + 1))
    echo "Request failed: /api/chaos/health"
  fi

  sleep "${DELAY_SECONDS}"
done

echo "Load finished. ok=${OK} fail=${FAIL}"
