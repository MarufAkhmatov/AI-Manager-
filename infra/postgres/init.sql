-- Bootstrap script run on first container start by the pgvector image.
-- Application schema is managed by Alembic; this file only enables the
-- pgvector extension so migrations can `CREATE TABLE ... vector(1024)`.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()
