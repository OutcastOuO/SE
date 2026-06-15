#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8080}"
VENV_DIR="${VENV_DIR:-.venv-chaos-gui}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Missing required command: python3" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Missing required command: docker" >&2
  exit 1
fi

if ! python3 -m venv --help >/dev/null 2>&1; then
  echo "python3 venv support is missing." >&2
  echo "Install it with: sudo apt update && sudo apt install -y python3-venv python3-pip" >&2
  exit 1
fi

if [[ -d "${VENV_DIR}" && ! -f "${VENV_DIR}/bin/activate" ]]; then
  echo "Found incomplete virtual environment at ${VENV_DIR}; rebuilding it."
  rm -rf "${VENV_DIR}"
fi

if [[ ! -f "${VENV_DIR}/bin/activate" ]]; then
  python3 -m venv "${VENV_DIR}"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.txt >/dev/null

echo "Starting VMS Chaos GUI at http://${HOST}:${PORT}"
python -m uvicorn chaos_gui:app --host "${HOST}" --port "${PORT}"
