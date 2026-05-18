# Claude operating notes — AI Manager Platform

This file is read by Claude Code at the start of every session in this repo.
Keep it short.

## Hard invariants (do not violate)

1. **Single runtime root.** All knowledge-base data, cache, temp files, logs,
   and processing outputs live under exactly one directory:
       `C:\Users\ASUS\Desktop\AI Manager`
   The path is configurable via the `AIM_ROOT` env var for dev only. Code
   must never read or write files outside the resolved root. Use
   `backend/app/security/paths.py::safe_join`; reject `..`, absolute escapes,
   and symlinks.

2. **AI Secure runs last on every response.** No agent's output may be
   returned to the user without passing through `agents/secure.py`.

3. **Shadow-guard for Lotus.** Any payload originating from a document with
   `documents.is_confidential = true` must have `id`, `title`, `source_url`,
   and `raw_path` stripped before it leaves the Shadow agent. The API
   serializer re-applies the rule defensively.

4. **Outbound network whitelist.** Only the Regulyator process may make
   outbound HTTP calls, and only to `lex.uz`, `cbu.uz`, `ipakyulibank.uz`.
   All other processes use a deny-by-default `httpx` transport. Local LLM
   (Ollama) and local Postgres/Redis are not "outbound".

5. **Branch.** All development happens on
   `claude/ai-manager-platform-design-d0t6k`. Open one PR per phase
   (see `/root/.claude/plans/...` and `docs/DESIGN.md`).

## Layout

- `docs/DESIGN.md` — full system design (architecture, agents, pipeline,
  DB schema, API, UI, security). Read this first.
- `backend/` — FastAPI app, agents, pipeline, watcher, crawler, DB models.
- `frontend/` — Next.js 14 app.
- `infra/` — `docker-compose.yml`, `postgres/init.sql`.
- `scripts/` — bootstrap and seed scripts.

## When in doubt

- Prefer reusing the design in `docs/DESIGN.md` over inventing new structure.
- Don't add agents beyond the 7 specified.
- Don't add external API integrations beyond the 3 whitelisted regulators.
