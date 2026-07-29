-- JobPilot AI — PostgreSQL initialization
-- Extensions and base configuration

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create application database user if not exists (handled by docker-compose env)
-- This file runs on first database initialization only
