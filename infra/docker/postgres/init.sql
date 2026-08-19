-- JobPilot AI — PostgreSQL initialization
-- Extensions and base configuration

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- pgvector ships with the pgvector/pgvector image but not with the stock
-- postgres image. A hard CREATE EXTENSION there aborts database
-- initialization, so treat it as optional.
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS "vector";
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'pgvector unavailable, skipping (semantic search falls back to in-app scoring)';
END
$$;

-- Create application database user if not exists (handled by docker-compose env)
-- This file runs on first database initialization only
