# AI Manager Platform — System Design

A local-first, multi-agent compliance platform. All runtime data lives under a single root on the operator's workstation; nothing sensitive leaves the machine.

```
ROOT (mandatory, hard-coded):
C:\Users\ASUS\Desktop\AI Manager
```

The platform boots, scans this root, classifies every existing file, reorganizes
it into the canonical KB layout, processes it into a vector-ready knowledge
base, and then keeps watching the root for changes.

---

## 1. System Overview

| Layer                | Technology                              |
|----------------------|------------------------------------------|
| Frontend             | Next.js 14 (App Router) + Tailwind + Framer Motion |
| Backend              | FastAPI (Python 3.11) + Uvicorn         |
| Agent runtime        | LangGraph orchestration over local LLM  |
| LLM (local)          | Ollama (llama3.1 / qwen2.5) — no cloud  |
| Embeddings (local)   | bge-m3 via Ollama / sentence-transformers |
| Vector store         | PostgreSQL 16 + pgvector 0.7            |
| Cache / queue        | Redis 7 (job queue + agent response cache) |
| File watcher         | watchdog (Python) + polling fallback    |
| OCR                  | Tesseract 5 (+ language packs)          |
| Auth                 | Local JWT + bcrypt                      |
| Packaging            | Docker Compose (single-host, all local) |

**Agents (7 total):** 1 orchestrator (AI Manager) + 6 specialists (AI Metodist,
AI Regulyator, AI Shadow, AI Secure, AI Searcher, AI Architect).

---

## 2. High-Level System Architecture

```
                          ┌───────────────────────────────────────────┐
                          │                  USER                     │
                          │   (browser, localhost, dark/glass UI)     │
                          └────────────────────┬──────────────────────┘
                                               │  HTTPS (local TLS)
                                               ▼
                          ┌───────────────────────────────────────────┐
                          │          Next.js Frontend (3000)          │
                          │   Login · Dashboard · Per-agent pages     │
                          │   AI Manager chat + workflow viz (n8n)    │
                          └────────────────────┬──────────────────────┘
                                               │  REST + WebSocket
                                               ▼
                          ┌───────────────────────────────────────────┐
                          │          FastAPI Backend (8000)           │
                          │  Routers · Auth · WS hub · Job queue API  │
                          └─────┬──────────────────┬──────────────────┘
                                │                  │
                ┌───────────────▼───┐    ┌─────────▼──────────┐
                │  AI Manager       │    │  AI Architect      │
                │  (LangGraph DAG)  │◄──►│  (file lifecycle)  │
                └─────┬─────────────┘    └─────────┬──────────┘
                      │ parallel fan-out           │ watches FS
       ┌──────────┬───┴───┬──────────┬─────────┐   │
       ▼          ▼       ▼          ▼         ▼   ▼
  ┌────────┐ ┌────────┐┌────────┐┌────────┐┌────────┐┌────────────┐
  │Metodist│ │Regulyat││Shadow  ││Secure  ││Searcher││ Pipeline    │
  │        │ │ or     ││        ││(mask)  ││(pgvec) ││ OCR→Chunk→  │
  │        │ │        ││        ││        ││        ││ Embed→Store │
  └───┬────┘ └───┬────┘└───┬────┘└───┬────┘└───┬────┘└─────┬───────┘
      │          │         │         │         │           │
      └──────────┴─────────┴─────────┴─────────┴─────┐     │
                                                     ▼     ▼
                              ┌────────────────────────────────────┐
                              │  PostgreSQL 16 + pgvector          │
                              │  documents · document_chunks ·     │
                              │  processed_files · agent_logs ·    │
                              │  tasks                             │
                              └────────────────────────────────────┘
                              ┌────────────────────────────────────┐
                              │  Redis 7   (cache · job queue)     │
                              └────────────────────────────────────┘
                              ┌────────────────────────────────────┐
                              │  Ollama (LLM + embeddings, local)  │
                              └────────────────────────────────────┘
                              ┌────────────────────────────────────┐
                              │  ROOT: C:\Users\ASUS\Desktop\AI    │
                              │  Manager  (KB / Archive / Logs /   │
                              │  Cache)                            │
                              └────────────────────────────────────┘
```

Every box runs on the operator's machine. There are exactly two outbound
network destinations and only AI Regulyator may reach them: `lex.uz`,
`cbu.uz`, `ipakyulibank.uz` (whitelist enforced at the HTTP client layer).

---

## 3. Knowledge Base Folder Structure (runtime, mandatory)

```
C:\Users\ASUS\Desktop\AI Manager\
├── KB\
│   ├── Regulator\          # external regulations (lex.uz, cbu.uz, ipakyuli)
│   │   ├── lex_uz\
│   │   ├── cbu_uz\
│   │   └── ipakyulibank\
│   ├── Lotus\              # internal confidential (AI Shadow domain)
│   │   └── <issuing_authority>\<YYYY>\
│   ├── Processed\          # cleaned + chunked text artifacts (.jsonl)
│   │   └── <doc_id>\chunks.jsonl
│   ├── Raw\                # original binary inputs verbatim (immutable)
│   │   └── <doc_id>\original.<ext>
│   └── Temp\               # OCR scratch, conversion intermediates (TTL 24h)
├── Archive\                # deprecated / superseded documents
│   └── <YYYY-MM>\
├── Logs\
│   ├── agents\<agent>.log
│   ├── pipeline\pipeline.log
│   ├── api\access.log
│   └── audit\audit.jsonl   # append-only, signed
└── Cache\
    ├── embeddings\         # content-hash → vector blobs
    ├── ocr\                # page-image hash → extracted text
    └── responses\          # query hash → final response (TTL configurable)
```

**Rules enforced by AI Architect:**
- No file is created or moved outside this root, ever.
- `Raw\` is write-once. Re-ingestion creates a new `doc_id`.
- `Lotus\` is read-restricted: only AI Shadow's process may open these paths.
- `Temp\` is purged on a 24h sweep.
- `Cache\` keys are content-hashes; the cache is reproducible and disposable.

---

## 4. Repository / Module Structure (this codebase)

```
ai-manager-platform/
├── docs/
│   └── DESIGN.md                  ← this document
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI entrypoint
│   │   ├── config.py              # Settings (root path, DB URL, etc.)
│   │   ├── deps.py                # DI: db session, redis, agent registry
│   │   ├── api/
│   │   │   ├── routes_auth.py
│   │   │   ├── routes_chat.py     # /api/chat  → AI Manager
│   │   │   ├── routes_agents.py   # /api/agents/<name>/...
│   │   │   ├── routes_kb.py       # /api/kb/...
│   │   │   ├── routes_tasks.py    # /api/tasks/...
│   │   │   └── ws_hub.py          # /ws/activity (real-time panel)
│   │   ├── agents/
│   │   │   ├── base.py            # BaseAgent contract
│   │   │   ├── manager.py         # AI Manager (LangGraph)
│   │   │   ├── metodist.py
│   │   │   ├── regulyator.py
│   │   │   ├── shadow.py
│   │   │   ├── secure.py          # output sanitizer (always last)
│   │   │   ├── searcher.py
│   │   │   └── architect.py       # filesystem + pipeline owner
│   │   ├── pipeline/
│   │   │   ├── ingest.py          # classify + route to Raw/Lotus
│   │   │   ├── ocr.py             # Tesseract wrapper
│   │   │   ├── normalize.py       # unicode/whitespace/section detection
│   │   │   ├── chunker.py         # 500–1000 token semantic chunks
│   │   │   ├── embedder.py        # bge-m3, cache by content hash
│   │   │   └── storage.py         # writes to Postgres + Processed\
│   │   ├── watcher/
│   │   │   ├── fs_watch.py        # watchdog observer
│   │   │   └── scanner.py         # initial full scan + reorganize
│   │   ├── crawler/
│   │   │   ├── lex_uz.py
│   │   │   ├── cbu_uz.py
│   │   │   └── ipakyulibank.py
│   │   ├── security/
│   │   │   ├── masking.py         # PII rules (names, phones, accounts)
│   │   │   ├── shadow_guard.py    # forbid leaking doc id/name/source
│   │   │   └── audit.py
│   │   ├── db/
│   │   │   ├── models.py
│   │   │   ├── session.py
│   │   │   └── migrations/        # alembic
│   │   └── llm/
│   │       ├── ollama_client.py
│   │       └── embeddings.py
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── (auth)/login/page.tsx
│   │   ├── dashboard/page.tsx
│   │   ├── manager/page.tsx       # chat + activity + workflow viz
│   │   ├── agents/[name]/page.tsx
│   │   ├── kb/page.tsx
│   │   └── layout.tsx
│   ├── components/
│   │   ├── AgentNode.tsx          # circular neomorphic icon
│   │   ├── WorkflowCanvas.tsx     # n8n-style DAG (React Flow)
│   │   ├── ActivityPanel.tsx      # WS feed of agent events
│   │   ├── ChatPanel.tsx
│   │   └── ui/                    # glass + neomorphic primitives
│   ├── lib/api.ts
│   ├── styles/globals.css         # black/white dark theme tokens
│   ├── package.json
│   └── Dockerfile
├── infra/
│   ├── docker-compose.yml         # postgres+pgvector, redis, ollama, api, web
│   ├── postgres/init.sql          # CREATE EXTENSION vector; schemas
│   └── nginx/                     # local TLS termination (optional)
├── scripts/
│   ├── bootstrap_root.ps1         # creates C:\Users\ASUS\Desktop\AI Manager
│   └── seed_demo.py
├── .env.example
└── README.md
```

---

## 5. Agent Interaction Diagram

```
                        ┌─────────────────────────┐
                        │   User Query (chat)     │
                        └───────────┬─────────────┘
                                    ▼
                        ┌─────────────────────────┐
                        │      AI Manager         │
                        │  1. intent detection    │
                        │  2. agent selection     │
                        │  3. plan (DAG)          │
                        │  4. parallel dispatch   │
                        └─┬────────┬────────┬─────┘
                          │        │        │
        ┌─────────────────┘        │        └──────────────────────┐
        │                          │                               │
        ▼                          ▼                               ▼
 ┌─────────────┐           ┌─────────────┐                 ┌─────────────┐
 │ AI Searcher │           │ AI Metodist │                 │  AI Shadow  │
 │ pgvector    │           │ normative   │                 │ internal    │
 │ top-k + RRF │           │ diff/gaps   │                 │ confidential│
 └──────┬──────┘           └──────┬──────┘                 └──────┬──────┘
        │                         │                               │
        │                         ▼                               │
        │                 ┌─────────────┐                         │
        │                 │AI Regulyator│ (async, scheduled;      │
        │                 │ ext. crawl  │  feeds KB, rarely on    │
        │                 └─────────────┘  the critical path)     │
        │                                                         │
        └──────────────────────────┬──────────────────────────────┘
                                   ▼
                        ┌─────────────────────────┐
                        │  Manager aggregation    │
                        │  (merge + rank + cite)  │
                        └───────────┬─────────────┘
                                    ▼
                        ┌─────────────────────────┐
                        │   AI Secure (mandatory) │
                        │  PII masking            │
                        │  Shadow-guard scrub     │
                        └───────────┬─────────────┘
                                    ▼
                        ┌─────────────────────────┐
                        │     Final Response      │
                        └─────────────────────────┘

   Cross-cutting (always-on):
   ┌─────────────────────────────────────────────────────────────┐
   │  AI Architect — owns FS, ingestion, OCR, chunk, embed.       │
   │  Emits events to Searcher (new vectors) and Manager (status).│
   └─────────────────────────────────────────────────────────────┘
```

**Selection rules used by AI Manager:**

| Intent                                       | Agents activated                       |
|---------------------------------------------|----------------------------------------|
| "find me regulation X"                       | Searcher → Secure                      |
| "is this internal policy compliant?"         | Metodist + Searcher → Secure           |
| "what changed in CBU rules this week?"       | Regulyator (cached) + Searcher → Secure|
| "summarize this internal Lotus document"     | Shadow + Searcher → Secure             |
| "ingest this folder"                         | Architect (Manager just observes)      |

AI Secure is **non-optional** — it sits on the egress edge of every response.

---

## 6. Processing Pipeline Diagram

```
   ┌───────────────────────────────────────────────────────────────┐
   │ Trigger: watchdog event OR initial full scan OR crawler push   │
   └────────────────────────────┬──────────────────────────────────┘
                                ▼
              [1] File ingestion (AI Architect)
                  - compute sha256
                  - dedupe against documents.hash
                  - assign doc_id (uuid)
                  - copy original → KB\Raw\<doc_id>\original.<ext>
                                ▼
              [2] Classification
                  - rule + zero-shot LLM tag
                  - categories: regulator | lotus | internal-policy | other
                  - sensitive? → route to KB\Lotus\... (Shadow domain)
                                ▼
              [3] OCR  (Tesseract; skipped if text-native PDF/DOCX/TXT)
                  - per-page; cache by page-image hash in Cache\ocr\
                                ▼
              [4] Text normalization
                  - unicode NFC, dehyphenation, whitespace
                  - section/heading detection (regex + heuristics)
                                ▼
              [5] Chunking  (500–1000 tokens, semantic-aware)
                  - prefer section boundaries
                  - 15% overlap
                                ▼
              [6] Embedding generation  (bge-m3 via Ollama)
                  - cache by chunk-content hash
                                ▼
              [7] Vector store write  (Postgres + pgvector)
                  - INSERT into document_chunks
                  - HNSW index updated
                                ▼
              [8] Processed artifact write
                  - KB\Processed\<doc_id>\chunks.jsonl
                                ▼
              [9] Metadata tagging
                  - documents row: category, authority, dates, status
                  - emit WS event: "kb.document.indexed"
                                ▼
              [10] Supersede check (Regulator stream)
                  - if newer revision detected → mark older deprecated
                  - move to Archive\<YYYY-MM>\
```

Failure handling: each stage is idempotent and resumable; a `tasks` row tracks
stage, attempts, and last error. A failed stage retries with exponential
backoff (3 attempts) and on final failure raises an audit event.

---

## 7. Database Design

PostgreSQL 16 with `CREATE EXTENSION IF NOT EXISTS vector;`

```sql
-- documents: one row per logical document
CREATE TABLE documents (
    id              UUID PRIMARY KEY,
    sha256          CHAR(64) UNIQUE NOT NULL,
    title           TEXT,
    category        TEXT NOT NULL,          -- regulator|lotus|internal|other
    authority       TEXT,                   -- e.g. 'CBU', 'lex.uz', issuer
    source_url      TEXT,                   -- null for Lotus
    raw_path        TEXT NOT NULL,          -- KB\Raw\<id>\original.<ext>
    processed_path  TEXT,                   -- KB\Processed\<id>\chunks.jsonl
    status          TEXT NOT NULL,          -- active|deprecated|archived
    is_confidential BOOLEAN NOT NULL DEFAULT FALSE,
    issued_at       DATE,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    superseded_by   UUID REFERENCES documents(id),
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX ON documents (category, status);
CREATE INDEX ON documents (authority);

-- document_chunks: vector store
CREATE TABLE document_chunks (
    id              BIGSERIAL PRIMARY KEY,
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index     INT  NOT NULL,
    content         TEXT NOT NULL,
    token_count     INT  NOT NULL,
    embedding       vector(1024) NOT NULL,   -- bge-m3 dim
    content_hash    CHAR(64) NOT NULL,
    section_path    TEXT,
    UNIQUE (document_id, chunk_index)
);
CREATE INDEX document_chunks_hnsw
    ON document_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON document_chunks (content_hash);

-- processed_files: per-stage pipeline ledger
CREATE TABLE processed_files (
    id              BIGSERIAL PRIMARY KEY,
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    stage           TEXT NOT NULL,          -- ocr|normalize|chunk|embed|store
    status          TEXT NOT NULL,          -- pending|running|done|failed
    attempts        INT  NOT NULL DEFAULT 0,
    last_error      TEXT,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ
);
CREATE INDEX ON processed_files (document_id, stage);

-- agent_logs: per-invocation trace (drives Activity Panel)
CREATE TABLE agent_logs (
    id              BIGSERIAL PRIMARY KEY,
    task_id         UUID,
    agent           TEXT NOT NULL,          -- 'AI Manager', 'AI Searcher', ...
    event           TEXT NOT NULL,          -- start|tool|finish|error
    payload         JSONB NOT NULL,
    ms_elapsed      INT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON agent_logs (task_id, created_at);

-- tasks: a unit of orchestrated work (user query OR pipeline job)
CREATE TABLE tasks (
    id              UUID PRIMARY KEY,
    kind            TEXT NOT NULL,          -- chat|ingest|crawl|reindex
    status          TEXT NOT NULL,          -- queued|running|done|failed
    user_id         UUID,
    input           JSONB NOT NULL,
    output          JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ
);
CREATE INDEX ON tasks (status, kind);
```

---

## 8. API Design (FastAPI)

All routes are prefixed `/api`. WebSocket endpoint is `/ws/activity`.

### Auth

| Method | Path                | Body / params               | Returns                |
|-------:|---------------------|------------------------------|-------------------------|
| POST   | `/api/auth/login`   | `{username, password}`       | `{access_token, user}` |
| POST   | `/api/auth/logout`  | —                            | `204`                  |
| GET    | `/api/auth/me`      | —                            | current user           |

### Chat (AI Manager)

| Method | Path                | Body                                          | Returns                 |
|-------:|---------------------|-----------------------------------------------|--------------------------|
| POST   | `/api/chat`         | `{message, conversation_id?, mode?}`          | `{task_id, response, citations, agents_used}` |
| GET    | `/api/chat/{task}`  | —                                             | task trace + final answer|

### Agents (introspection + direct invocation, dev/admin)

| Method | Path                                | Purpose                          |
|-------:|--------------------------------------|----------------------------------|
| GET    | `/api/agents`                        | list 7 agents + status           |
| GET    | `/api/agents/{name}`                 | agent detail + recent logs       |
| POST   | `/api/agents/{name}/invoke`          | direct call (admin only)         |
| GET    | `/api/agents/{name}/logs`            | paginated agent_logs             |

### Knowledge Base

| Method | Path                                | Purpose                          |
|-------:|--------------------------------------|----------------------------------|
| GET    | `/api/kb/stats`                      | counts by category/status        |
| GET    | `/api/kb/documents`                  | search/filter (non-Lotus)        |
| GET    | `/api/kb/documents/{id}`             | metadata only; Lotus blocked     |
| POST   | `/api/kb/reindex`                    | admin: full rescan + reorganize  |
| POST   | `/api/kb/upload`                     | drop file into KB\Raw via API    |

### Tasks / Pipeline

| Method | Path                                | Purpose                          |
|-------:|--------------------------------------|----------------------------------|
| GET    | `/api/tasks`                         | list tasks (filter by kind/status)|
| GET    | `/api/tasks/{id}`                    | detail incl. processed_files     |
| POST   | `/api/tasks/{id}/retry`              | retry failed stage               |

### WebSocket

`/ws/activity` — broadcasts JSON events:
```
{"ts":"...","task_id":"...","agent":"AI Searcher","event":"tool",
 "payload":{"op":"vector_search","k":8,"latency_ms":42}}
```
Used by the AI Manager page's real-time activity panel and workflow canvas.

---

## 9. Data Flow Diagrams

### 9.1 Query path (user → answer)

```
Browser ──POST /api/chat──► FastAPI
                              │
                              ▼
                       AI Manager (LangGraph)
                              │
              ┌───────────────┼────────────────┐
              ▼               ▼                ▼
        AI Searcher     AI Metodist       AI Shadow (cond.)
        (pgvector)      (rules KB)        (Lotus only)
              │               │                │
              └───────────────┴────────────────┘
                              ▼
                       Aggregator (Manager)
                              ▼
                         AI Secure  ── masking rules
                              ▼
                         Response  ◄── cache write (Cache\responses)
                              ▼
                          Browser

   In parallel: agent_logs rows + WS events stream to /ws/activity.
```

### 9.2 Ingestion path (new file in root)

```
KB\Raw\ (or any subfolder of ROOT) ── watchdog event
                              ▼
                       AI Architect
                              ▼
              classify ──► route (Regulator | Lotus | Processed)
                              ▼
                  pipeline.run(doc_id)
        OCR → normalize → chunk → embed → store
                              ▼
              documents + document_chunks rows
                              ▼
              WS event: kb.document.indexed
                              ▼
              AI Searcher picks up via DB (no extra wiring)
```

### 9.3 External crawl path (daily)

```
Cron (APScheduler 03:00 local)
        ▼
 AI Regulyator
   ├─ fetch lex.uz index
   ├─ fetch cbu.uz index
   └─ fetch ipakyulibank.uz index
        ▼
 diff vs documents.source_url + sha256
        ▼
 download new docs → KB\Raw\<doc_id>\
        ▼
 mark superseded versions: status='deprecated', move to Archive\
        ▼
 Architect picks up via watchdog → pipeline runs
```

---

## 10. Module Breakdown

### Backend modules (responsibility, key inputs/outputs)

| Module                | Owns                                                   | Talks to                    |
|-----------------------|--------------------------------------------------------|-----------------------------|
| `api/`                | HTTP + WS surface                                      | agents, db                  |
| `agents/manager.py`   | LangGraph DAG, intent → plan → fan-out → aggregate     | all other agents, llm       |
| `agents/metodist.py`  | normative diff, gap/conflict detection                 | searcher, llm               |
| `agents/regulyator.py`| scheduled crawl, dedupe, supersede                     | crawler/, architect         |
| `agents/shadow.py`    | Lotus access; outputs summary-only payloads            | searcher (scoped), llm      |
| `agents/secure.py`    | final-stage sanitizer; runs on every response          | masking, shadow_guard       |
| `agents/searcher.py`  | embed query, pgvector top-k, RRF re-rank, cache        | db, llm/embeddings, redis   |
| `agents/architect.py` | FS watcher, classification, pipeline orchestration     | pipeline/, db               |
| `pipeline/`           | OCR, normalize, chunk, embed, store                    | Tesseract, ollama, db       |
| `watcher/`            | initial scan + live observer                           | architect                   |
| `crawler/`            | site-specific scrapers (whitelisted hosts)             | regulyator                  |
| `security/`           | PII masking, shadow-guard, append-only audit           | secure, shadow              |
| `db/`                 | SQLAlchemy models + Alembic migrations                 | postgres                    |
| `llm/`                | Ollama client + embedding wrapper with cache           | ollama, redis               |

### Frontend modules

| Module                  | Purpose                                                  |
|-------------------------|----------------------------------------------------------|
| `app/(auth)/login`      | local login form (JWT)                                   |
| `app/dashboard`         | 7 circular agent nodes (neomorphic), live status pings   |
| `app/manager`           | chat + ActivityPanel (WS) + WorkflowCanvas (React Flow)  |
| `app/agents/[name]`     | per-agent page: description, recent logs, manual invoke  |
| `app/kb`                | KB browser: stats, documents (Lotus rows masked to "—")  |
| `components/ui`         | glass + neomorphic primitives (Card, Button, Input)      |
| `lib/api.ts`            | typed fetcher + WS client                                |

### Agents — detailed contract

```python
class BaseAgent(Protocol):
    name: str
    async def run(self, ctx: AgentContext) -> AgentResult: ...
    # ctx carries: task_id, user, query, shared scratchpad, deadline
    # result carries: payload, citations, confidence, ms_elapsed
```

Manager builds the plan, dispatches via `asyncio.gather`, enforces a 3s
soft deadline (per perf requirement), and always pipes the merged result
through `AI Secure` before returning.

---

## 11. UI Specification

- **Theme:** pure black `#000` background, white `#fff` text, single accent
  (cool cyan `#7CE7FF`) used only for active/processing states.
- **Style:** neomorphic raised cards on glass (`backdrop-filter: blur(18px)`,
  1px inner highlight, 24px outer soft shadow). Corners 20px.
- **Login:** centered glass card; username/password; subtle agent-icon halo.
- **Dashboard:** 7 circular agent icons arranged in a hex layout around the
  AI Manager core. Each node pulses when active; click → agent page.
- **AI Manager page** (3-pane):
  1. left: conversation list,
  2. center: chat,
  3. right: Activity Panel (live WS feed) + WorkflowCanvas (React Flow
     DAG of the current task, n8n-style nodes/edges).
- **Per-agent page:** description, current status, last 50 events, quick
  "invoke" form (admin only).
- **KB page:** stats tiles + documents table; rows where `is_confidential`
  is true show only `summary · date · authority` — title/path/source are
  rendered as `—` regardless of viewer role (Shadow-guard at the renderer).

---

## 12. Performance Strategy (< 3s response)

- Local model defaults: `qwen2.5:7b-instruct` for routing, `llama3.1:8b`
  for synthesis. Both warm-loaded in Ollama at startup.
- AI Manager dispatches sub-agents in parallel (`asyncio.gather`) with a
  per-agent soft deadline of 2.2s; slowest agents return partial.
- pgvector HNSW with `m=16, ef_construction=64`; query `ef_search=40`.
- Three caches:
  1. **Embeddings cache** — keyed by chunk content hash; eliminates re-embed.
  2. **OCR cache** — keyed by page-image hash.
  3. **Response cache** — keyed by `(normalized_query, user_role)`; TTL 1h
     for Regulator queries, 5 min for Lotus queries.
- Streaming responses over WS for chat tokens; first byte target < 600ms.

---

## 13. Security Model

| Requirement                          | Enforcement                                  |
|--------------------------------------|-----------------------------------------------|
| 100% local processing                | Ollama local; outbound HTTP whitelist allows only `lex.uz`, `cbu.uz`, `ipakyulibank.uz`, and only from the Regulyator process. |
| Confidential masking                 | AI Secure runs as the last node of every response DAG; refuses to emit unless it has processed the payload. |
| No metadata leakage (Shadow)         | `shadow_guard` strips `title`, `source_url`, `raw_path`, `id` from any payload originating from `is_confidential=true` documents. API serializers re-apply the rule defensively. |
| PII masking                          | Regex + NER (local) for names, phones (incl. UZ formats), bank account / card patterns, INN/PINFL. |
| Audit                                | Append-only `Logs\audit\audit.jsonl` with hash chain (prev_hash field). |
| Auth                                 | Local JWT (HS256), bcrypt password hashes, role-based (admin / analyst / viewer). |
| FS confinement                       | All path operations go through `safe_join(ROOT, ...)`; symlinks rejected. |

---

## 14. Bootstrap Flow (first run)

1. `bootstrap_root.ps1` ensures `C:\Users\ASUS\Desktop\AI Manager\` and all
   required subfolders exist; sets ACLs so only the service account can
   read `KB\Lotus\`.
2. `docker compose up` starts postgres+pgvector, redis, ollama, api, web.
3. API runs Alembic migrations, pulls `qwen2.5`, `llama3.1`, `bge-m3` in
   Ollama if missing.
4. AI Architect performs a **full scan** of ROOT, classifies every file,
   moves it into the canonical layout, and enqueues pipeline jobs.
5. Watcher starts. AI Regulyator schedules its daily crawl. UI becomes
   reachable at `https://localhost`.

---

## 15. Deliverables Checklist (mapped to the request)

- [x] Full system architecture diagram — §2
- [x] Detailed folder structure (runtime KB + repo) — §3, §4
- [x] Agent interaction diagram — §5
- [x] Processing pipeline diagram — §6
- [x] Module breakdown (backend, frontend, agents) — §10
- [x] API design — §8
- [x] Data flow diagrams — §9
- [x] Database design — §7
- [x] UI requirements — §11
- [x] Performance plan — §12
- [x] Security model — §13
