#!/usr/bin/env bash
# Local dev helper: boots FastAPI + Vite together (Git Bash / WSL / macOS).
# Must use LF line endings — CRLF breaks the shebang under WSL ("bash\r" errors).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export DRONE_NAV_DATA_DIR="${DRONE_NAV_DATA_DIR:-$ROOT/data}"

is_wsl() {
  [[ -n "${WSL_INTEROP:-}" ]] || grep -qi microsoft /proc/version 2>/dev/null || false
}

ensure_backend_python() {
  local vpy="$ROOT/backend/.venv/bin/python"
  local vpip="$ROOT/backend/.venv/bin/pip"

  if [[ ! -x "$vpy" ]]; then
    echo "[backend] Creating .venv under backend/ ..."
    python3 -m venv "$ROOT/backend/.venv"
    "$vpip" install -U pip
    "$vpip" install -r "$ROOT/backend/requirements.txt"
  fi

  if ! "$vpy" -c "import fastapi" 2>/dev/null; then
    echo "[backend] Installing deps into .venv ..."
    "$vpip" install -r "$ROOT/backend/requirements.txt"
  fi
}

ensure_frontend_node_modules() {
  local front="$ROOT/frontend"
  local nm="$front/node_modules"

  reinstall() {
    echo "[frontend] Running npm install in $front ..."
    rm -rf "$nm"
    (cd "$front" && npm install)
  }

  if [[ ! -d "$nm" ]]; then
    reinstall
    return 0
  fi

  if is_wsl; then
    shopt -s nullglob
    local rollup_linux_matches=( "$nm"/@rollup/rollup-*-linux* )
    shopt -u nullglob
    if [[ ${#rollup_linux_matches[@]} -eq 0 ]]; then
      echo "[frontend] Detected WSL/Linux Node but npm deps look Windows-only (missing @rollup/*-linux)."
      reinstall
    fi
  fi
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Drone visual navigation · local inspector"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Data directory: ${DRONE_NAV_DATA_DIR}"
echo "Backend:  http://127.0.0.1:8000  (FastAPI · backend/.venv)"
echo "Frontend: http://127.0.0.1:5173  (Vite)"
echo "Press Ctrl+C to stop both servers."
echo

ensure_backend_python
ensure_frontend_node_modules

trap 'kill $(jobs -p) 2>/dev/null || true' EXIT INT TERM

(
  cd "$ROOT/backend"
  "$ROOT/backend/.venv/bin/python" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
) &

(
  cd "$ROOT/frontend"
  npm run dev
) &

wait
