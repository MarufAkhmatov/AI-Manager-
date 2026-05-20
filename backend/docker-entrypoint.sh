#!/usr/bin/env bash
# Backend container entrypoint: migrate → seed admin → serve.
set -euo pipefail

echo "[entrypoint] running database migrations (alembic upgrade head)…"
alembic upgrade head

if [ -n "${ADMIN_USERNAME:-}" ] && [ -n "${ADMIN_PASSWORD:-}" ]; then
    echo "[entrypoint] seeding admin user (idempotent)…"
    python -m app.seed || echo "[entrypoint] admin seed failed (non-fatal), continuing"
fi

# Warm the local models in the background so the first real query doesn't pay
# the cold-load penalty (a 7B model takes ~60-70s to load on CPU, far past the
# agent deadlines). keep_alive=-1 keeps them resident. Non-fatal: if Ollama is
# briefly unavailable the agents still fall back gracefully.
if [ "${AIM_DEMO:-0}" != "1" ]; then
    echo "[entrypoint] warming Ollama models in background…"
    python - <<'PY' &
import os, httpx
host = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
jobs = [
    ("/api/embed", {"model": os.environ.get("OLLAMA_MODEL_EMBED", "bge-m3"),
                    "input": "warmup", "keep_alive": -1}),
    ("/api/generate", {"model": os.environ.get("OLLAMA_MODEL_ROUTER", "qwen2.5:7b-instruct"),
                       "prompt": "ok", "stream": False, "keep_alive": -1}),
    ("/api/generate", {"model": os.environ.get("OLLAMA_MODEL_SYNTH", "llama3.1:8b"),
                       "prompt": "ok", "stream": False, "keep_alive": -1}),
]
for ep, payload in jobs:
    try:
        httpx.post(host + ep, json=payload, timeout=300)
    except Exception as e:  # noqa: BLE001
        print(f"[warmup] {payload['model']} failed: {e}", flush=True)
PY
fi

echo "[entrypoint] starting API on :8000 (workers=${API_WORKERS:-2})…"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${API_WORKERS:-2}"
