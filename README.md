# AI Manager Platform

Local-first multi-agent compliance platform for the Uzbek regulatory
context. All data — knowledge base, cache, logs, processing outputs —
lives under one mandatory runtime root:

    C:\Users\ASUS\Desktop\AI Manager

Seven agents collaborate behind a FastAPI backend and a Next.js 14 UI:

| Agent          | Role                                                                |
|----------------|---------------------------------------------------------------------|
| AI Manager     | intent detection → DAG → parallel fan-out → aggregate               |
| AI Searcher    | pgvector top-k retrieval with Redis response cache                  |
| AI Metodist    | normative diff: conflicts, gaps, inconsistencies, impacted depts   |
| AI Shadow      | Lotus-only retrieval; outputs only summary, date, authority         |
| AI Secure      | mandatory egress sanitizer: PII masking + Shadow-guard              |
| AI Regulyator  | scheduled daily crawl of lex.uz, cbu.uz, ipakyulibank.uz            |
| AI Architect   | filesystem watcher + 10-stage ingestion pipeline                    |

The long-form architecture lives in [`docs/DESIGN.md`](docs/DESIGN.md).

## Quick start — demo mode (no Docker, ~2 minutes)

If you just want to see the dashboard talk to the backend on your laptop
without setting up Postgres / Redis / Ollama, run the demo launcher.
It boots:

* **FastAPI** with `AIM_DEMO=1` — stub Searcher / Metodist / Shadow that
  return canned responses (the AI Secure egress + Shadow-guard contracts
  are kept intact); login as `admin` with any password.
* **Next.js** dev server pointed at the local backend.

```powershell
# Windows (PowerShell, from the repo root)
.\scripts\start_demo.ps1
```

```bash
# Linux / macOS, from the repo root
./scripts/start_demo.sh
```

Open <http://localhost:3000/dashboard> and sign in as **admin / anything**.
Chat → Recommendation auto-suggest is live; the workflow canvas pulses
in real time when agents fire.

To switch to the real stack later, just drop `AIM_DEMO` and follow the
Docker quick-start below.

## Quick start (operator) — full stack with Docker

Prereqs: Docker Desktop (Windows/macOS) or Docker Engine + Compose v2
(Linux). ~12 GB free disk for the Ollama models, ~10 GB RAM.

### One command

```powershell
# Windows (PowerShell, from the repo root)
copy .env.example .env
#   edit .env: POSTGRES_PASSWORD, JWT_SECRET, ADMIN_PASSWORD, AIM_ROOT
.\scripts\prod_up.ps1
```

```bash
# Linux / macOS, from the repo root
cp .env.example .env
#   edit .env: POSTGRES_PASSWORD, JWT_SECRET, ADMIN_PASSWORD, AIM_ROOT
./scripts/prod_up.sh
```

The launcher builds the images and runs `docker compose up -d`. From there
everything is automatic:

1. **`ollama-init`** pulls the three local models (`qwen2.5:7b-instruct`,
   `llama3.1:8b`, `bge-m3`) — slow on the first run only (cached in a volume).
2. **`api`** waits for Postgres + Redis + the model pull, then its entrypoint
   runs `alembic upgrade head` and seeds the `ADMIN_USERNAME` / `ADMIN_PASSWORD`
   from your `.env` (idempotent), and starts uvicorn.
3. **`web`** starts once the API is healthy.

Then open <http://localhost:3000/dashboard> and sign in with your
`ADMIN_USERNAME` / `ADMIN_PASSWORD`. The API is at <http://localhost:8000>
(`/docs` for OpenAPI, `/ws/activity` for the live activity feed).

Follow startup:

```bash
docker compose --env-file .env -f infra/docker-compose.yml logs -f
```

### Equivalent manual steps

```powershell
powershell -ExecutionPolicy Bypass -File scripts\bootstrap_root.ps1   # KB tree + ACLs
docker compose --env-file .env -f infra\docker-compose.yml build
docker compose --env-file .env -f infra\docker-compose.yml up -d
# migrations + admin seed run automatically in the api entrypoint.
```

### AI Metodist (optional)

The `metodist` sub-agent wraps a separate `metodist-agent` package that
ships with the bank corpus and calls the Anthropic API. It is optional —
without it the platform still answers (Searcher + Shadow + Secure, with
conflict/recommendation extraction via the local Ollama model). To enable
it, mount the standalone into the `api` container, `pip install -e` it, and
set `ANTHROPIC_API_KEY`. See `backend/app/agents/metodist.py`.

## What happens at first start

1. `AI Architect` walks every file under `AIM_ROOT`, classifies each by
   its location, and enqueues the full ingestion pipeline (ingest →
   OCR → normalize → chunk → embed → store).
2. `watchdog` keeps watching the root for changes — anything you drop
   into `KB\Raw\` is picked up within seconds.
3. `AI Regulyator` schedules a daily crawl at 03:00 UTC (override via
   `CRAWL_CRON`) hitting only the three whitelisted regulator hosts.

## Operator commands

```powershell
# Reindex everything (also exposed as POST /api/kb/reindex, admin only):
docker compose exec api python -c "import asyncio; from app.agents.architect import architect; asyncio.run(architect.reindex())"

# Manual regulator crawl:
curl -X POST http://localhost:8000/api/agents/AI%20Regulyator/invoke \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" -d '{"query":""}'

# Verify the audit chain at Logs\audit\audit.jsonl:
docker compose exec api python -m scripts.verify_audit

# Stop / start:
docker compose -f infra\docker-compose.yml down
docker compose -f infra\docker-compose.yml up -d
```

## Backup

Only `AIM_ROOT` and the Postgres volume need backup. Both are
self-contained:

```powershell
# Snapshot the runtime root (live-safe; Raw\ is write-once, Lotus\ is rare):
robocopy "C:\Users\ASUS\Desktop\AI Manager" D:\Backups\aim /MIR

# Snapshot Postgres:
docker compose exec postgres pg_dump -U ai_manager ai_manager > D:\Backups\aim\postgres.sql
```

## Security invariants

- Every response passes through `AI Secure` — Manager refuses to return
  if it didn't.
- `AI Shadow` strips `id`, `title`, `source_url`, `raw_path` from any
  output; the Shadow-guard re-applies the rule in `AI Secure`.
- Outbound HTTP is locked to `lex.uz`, `cbu.uz`, `ipakyulibank.uz` via a
  per-crawler `WhitelistTransport`; everything else (Ollama, Postgres,
  Redis) is local.
- All path operations go through `safe_join(ROOT, …)` — symlinks and
  absolute components are rejected.
- The audit log is append-only and hash-chained; `scripts/verify_audit.py`
  validates the chain.

## Development (Linux/macOS)

```bash
# Point AIM_ROOT at a writable local directory in .env:
echo "AIM_ROOT=$PWD/aim-root" >> .env
mkdir -p aim-root/{KB/Regulator/{lex_uz,cbu_uz,ipakyulibank},KB/{Lotus,Processed,Raw,Temp},Archive,Logs/{agents,pipeline,api,audit},Cache/{embeddings,ocr,responses}}

# Stack:
docker compose -f infra/docker-compose.yml up -d

# Backend tests:
cd backend && pip install -e ".[dev]" && pytest

# Frontend dev:
cd frontend && npm install && npm run dev
```
