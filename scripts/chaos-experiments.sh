#!/usr/bin/env bash
set -euo pipefail

EXPERIMENT="${1:-restart}"
DURATION_SECONDS="${2:-30}"
BASE_URL="${BASE_URL:-http://localhost:8000}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Missing required command: docker" >&2
  exit 1
fi

if ! docker inspect vms-api >/dev/null 2>&1; then
  echo "Container vms-api does not exist. Run: docker compose up -d --build" >&2
  exit 1
fi

wait_for_api() {
  local tries="${1:-30}"
  for _ in $(seq 1 "${tries}"); do
    if curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
      echo "API health recovered."
      return 0
    fi
    sleep 2
  done
  echo "API health did not recover at ${BASE_URL}/health" >&2
  return 1
}

echo "Running chaos experiment: ${EXPERIMENT}"

case "${EXPERIMENT}" in
  kill)
    echo "Simulating app process crash by killing PID 1 inside vms-api..."
    docker exec vms-api sh -c "pkill uvicorn" >/dev/null 2>&1 || true
    wait_for_api 45
    ;;
  restart)
    docker restart vms-api
    wait_for_api 45
    ;;
  stop)
    docker stop vms-api
    sleep "${DURATION_SECONDS}"
    docker start vms-api
    wait_for_api 45
    ;;
  pause)
    docker pause vms-api
    sleep "${DURATION_SECONDS}"
    docker unpause vms-api
    wait_for_api 45
    ;;
  delay)
    echo "Starting Pumba network delay profile for about 45 seconds."
    docker compose --profile chaos rm -f -s pumba-delay >/dev/null 2>&1 || true
    if ! docker compose --profile chaos up --force-recreate --abort-on-container-exit --exit-code-from pumba-delay pumba-delay; then
      echo "Pumba delay failed." >&2
      echo "If the log says 'client version is too old', your Docker daemon requires API v1.44+." >&2
      echo "This project sets DOCKER_API_VERSION=1.44 for Pumba; recreate the service with docker compose up after pulling the latest files." >&2
      exit 1
    fi
    docker compose --profile chaos rm -f -s pumba-delay >/dev/null 2>&1 || true
    wait_for_api 30
    ;;
  *)
    echo "Unknown experiment: ${EXPERIMENT}" >&2
    echo "Usage: $0 kill|restart|stop|pause|delay [duration_seconds]" >&2
    exit 1
    ;;
esac

echo "Chaos experiment completed. Check Grafana and Prometheus for impact and recovery."
