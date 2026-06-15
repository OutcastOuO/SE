#!/usr/bin/env bash
set -euo pipefail

LOAD_SECONDS="${1:-120}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Missing required command: docker" >&2
  exit 1
fi

echo "Starting VMS chaos stack..."
docker compose up -d --build

echo "Waiting for API health..."
for _ in $(seq 1 30); do
  if curl -fsS "http://localhost:8000/health" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

"$(dirname "$0")/smoke-test.sh"

cat <<INFO
Start another terminal with:
  ./scripts/api-load.sh ${LOAD_SECONDS}

Then run one experiment, for example:
  ./scripts/chaos-experiments.sh restart

URLs:
  API        http://localhost:8000
  Prometheus http://localhost:9090
  Grafana    http://localhost:3000 admin/admin
  Portainer  http://localhost:9000
INFO
