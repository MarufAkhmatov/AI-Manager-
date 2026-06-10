#!/usr/bin/env bash
# start_demo.sh — one-shot launcher for the AI Manager Platform (Linux/macOS).
#
# Boots the backend in DEMO mode (no Postgres / Redis / Ollama / Docker
# required) and the Next.js dev server in parallel. Open the dashboard at
# http://localhost:3000/dashboard — login as admin (any password).
#
# Usage from the repo root:
#     ./scripts/start_demo.sh

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

echo "[AI Manager] starting backend (demo mode)…"

if [ ! -d .venv ]; then
    echo "  creating virtualenv at .venv …"
    python3 -m venv .venv
fi
# shellcheck source=/dev/null
source .venv/bin/activate

python -m pip install --upgrade pip --quiet
pip install --quiet --upgrade \
    "fastapi>=0.115" "uvicorn[standard]>=0.32" \
    "sqlalchemy[asyncio]>=2.0" "aiosqlite>=0.20" \
    "redis>=5.2" "httpx>=0.27" "tiktoken>=0.8" \
    "pydantic>=2.9" "pydantic-settings>=2.6" \
    "passlib[bcrypt]>=1.7" "pyjwt>=2.10" \
    "watchdog>=5" "apscheduler>=3.10" "pgvector>=0.3.6" \
    "python-multipart>=0.0.12"

export AIM_ROOT="$REPO/aim-demo-root"
export AIM_DEMO=1
export DATABASE_URL="sqlite+aiosqlite:///./aim-demo.db"
export JWT_SECRET="${JWT_SECRET:-demo-secret-replace-for-prod}"
export PYTHONPATH="$REPO/backend"
mkdir -p "$AIM_ROOT"

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
echo "  backend pid=$BACKEND_PID  →  http://localhost:8000"

cleanup() {
    echo
    echo "[AI Manager] stopping…"
    kill "$BACKEND_PID" 2>/dev/null || true
    kill "$FRONTEND_PID" 2>/dev/null || true
    wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "[AI Manager] starting frontend…"
cd "$REPO/frontend"
if [ ! -d node_modules ]; then
    echo "  npm install (legacy peer deps) …"
    npm install --legacy-peer-deps --no-audit --no-fund
fi
export NEXT_PUBLIC_API_BASE="http://localhost:8000"
export NEXT_PUBLIC_WS_BASE="ws://localhost:8000"
npm run dev &
FRONTEND_PID=$!

cat <<EOF

──────────────────────────────────────────────────────────────
 AI Manager Platform — demo mode running
──────────────────────────────────────────────────────────────
 Backend  : http://localhost:8000  (pid $BACKEND_PID)
 Frontend : http://localhost:3000  (pid $FRONTEND_PID)
 Dashboard: http://localhost:3000/dashboard
 Login    : username = admin   password = anything

 Ctrl+C to stop both.
──────────────────────────────────────────────────────────────

EOF

wait
