-- Memories schema: explicit grants + service_role maintenance access
-- Generated: 2026-01-19
--
-- Rationale:
-- - Supabase does not automatically grant USAGE on custom schemas created by migrations.
-- - The application uses the `memories` schema via PostgREST (supabase-js `.schema("memories")`).
-- - Seed scripts and background maintenance require `service_role` access for deterministic local dev.

-- NOTE: Supabase CLI can restore `supabase_migrations.schema_migrations` from a cached local backup.
-- If the tracking row for this migration already exists, the CLI will fail at the end when recording
-- the migration version. Make the migration idempotent by deleting any pre-existing row (when present).
DO $do$
BEGIN
  IF to_regclass('supabase_migrations.schema_migrations') IS NOT NULL THEN
    DELETE FROM supabase_migrations.schema_migrations WHERE version = '20260119021000';
  END IF;
END;
$do$;

BEGIN;

-- Schema usage for PostgREST roles.
GRANT USAGE ON SCHEMA memories TO authenticated, service_role;

-- Table privileges (RLS still applies for authenticated).
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA memories TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA memories TO service_role;

-- Sequences for identity columns (future-proof).
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA memories TO authenticated, service_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA memories
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA memories
  GRANT ALL ON TABLES TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA memories
  GRANT USAGE, SELECT ON SEQUENCES TO authenticated, service_role;

-- RLS: allow service_role full access (defense-in-depth; service role should be able to maintain).
DROP POLICY IF EXISTS memories_sessions_service_all ON memories.sessions;
CREATE POLICY memories_sessions_service_all
  ON memories.sessions
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

DROP POLICY IF EXISTS memories_turns_service_all ON memories.turns;
CREATE POLICY memories_turns_service_all
  ON memories.turns
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

DROP POLICY IF EXISTS memories_turn_embeddings_service_all ON memories.turn_embeddings;
CREATE POLICY memories_turn_embeddings_service_all
  ON memories.turn_embeddings
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

COMMIT;
