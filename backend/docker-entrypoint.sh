#!/usr/bin/env bash
# Backend container entrypoint: migrate → seed admin → serve.
set -euo pipefail

echo "[entrypoint] running database migrations (alembic upgrade head)…"
alembic upgrade head

if [ -n "${ADMIN_USERNAME:-}" ] && [ -n "${ADMIN_PASSWORD:-}" ]; then
    echo "[entrypoint] seeding admin user (idempotent)…"
    python -m app.seed || echo "[entrypoint] admin seed failed (non-fatal), continuing"
fi

echo "[entrypoint] starting API on :8000 (workers=${API_WORKERS:-2})…"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${API_WORKERS:-2}"
