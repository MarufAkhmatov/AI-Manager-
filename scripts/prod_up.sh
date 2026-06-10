#!/usr/bin/env bash
# prod_up.sh — bring up the full AI Manager production stack (Linux/macOS).
#
# One command: builds images, pulls Ollama models, runs migrations, seeds
# the admin, and starts every service. Run from the repo root:
#     ./scripts/prod_up.sh
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

# 1. .env
if [ ! -f .env ]; then
    echo "[prod] .env not found — copying from .env.example"
    cp .env.example .env
    echo "  >>> Edit .env: set POSTGRES_PASSWORD, JWT_SECRET, ADMIN_PASSWORD,"
    echo "      AIM_ROOT, and (optional) ANTHROPIC_API_KEY, then re-run."
    exit 1
fi

# 2. Ensure AIM_ROOT exists (KB tree). On Linux/macOS we just mkdir the tree;
#    the Windows bootstrap script handles ACLs on the operator's workstation.
AIM_ROOT="$(grep -E '^\s*AIM_ROOT=' .env | head -1 | cut -d= -f2- | tr -d '\r' | xargs || true)"
if [ -n "$AIM_ROOT" ] && [ ! -d "$AIM_ROOT" ]; then
    echo "[prod] creating KB tree under $AIM_ROOT"
    mkdir -p "$AIM_ROOT"/KB/{Regulator,Lotus,Processed,Raw,Temp} \
             "$AIM_ROOT"/Archive "$AIM_ROOT"/Logs/{agents,pipeline,api,audit} \
             "$AIM_ROOT"/Cache/{embeddings,ocr,responses}
fi

# --env-file makes ${AIM_ROOT} etc. available for compose interpolation
# (env_file: only injects into containers).
echo "[prod] building images…"
docker compose --env-file .env -f infra/docker-compose.yml build

echo "[prod] starting stack (first run pulls ~10GB of Ollama models — be patient)…"
docker compose --env-file .env -f infra/docker-compose.yml up -d

cat <<EOF

──────────────────────────────────────────────────────────────
 AI Manager Platform — production stack starting
──────────────────────────────────────────────────────────────
 Web : http://localhost:3000/dashboard
 API : http://localhost:8000/docs
 Login: the ADMIN_USERNAME / ADMIN_PASSWORD from your .env

 Follow startup:  docker compose --env-file .env -f infra/docker-compose.yml logs -f
 ollama-init pulls models on first run; api waits for it, then
 migrates + seeds the admin automatically.
──────────────────────────────────────────────────────────────
EOF
