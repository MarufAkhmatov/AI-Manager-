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

## Quick start (operator)

Prereqs: Windows 10/11 with Docker Desktop, Python 3.11 if you want to
run the seed and verifier scripts directly.

```powershell
# 1. Create the runtime root + lock ACLs on KB\Lotus.
powershell -ExecutionPolicy Bypass -File scripts\bootstrap_root.ps1

# 2. Configure secrets.
copy .env.example .env
# edit .env: set POSTGRES_PASSWORD and JWT_SECRET to strong values

# 3. Bring up the stack (postgres+pgvector, redis, ollama, api, web).
docker compose -f infra\docker-compose.yml up -d

# 4. Run database migrations.
docker compose -f infra\docker-compose.yml exec api alembic upgrade head

# 5. Pull local models in Ollama (one-time).
docker compose -f infra\docker-compose.yml exec ollama \
    sh -c "ollama pull qwen2.5:7b-instruct && \
           ollama pull llama3.1:8b && \
           ollama pull bge-m3"

# 6. Create the initial admin.
docker compose -f infra\docker-compose.yml exec api \
    python -m scripts.seed_admin --username admin --password 'strong-pwd' --role admin
```

The web UI is then at http://localhost:3000 and the API at
http://localhost:8000 (`/docs` for OpenAPI, `/ws/activity` for the
live agent activity feed).

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
