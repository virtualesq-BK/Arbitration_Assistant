-- Optional init script for the pgvector/pgvector:pg16 container.
-- Mount it with:  volumes: ["./docker/postgres-init.sql:/docker-entrypoint-initdb.d/01-init.sql:ro"]
-- The Alembic migration 001_initial also runs this statement, so mounting it is not required.
CREATE EXTENSION IF NOT EXISTS vector;
