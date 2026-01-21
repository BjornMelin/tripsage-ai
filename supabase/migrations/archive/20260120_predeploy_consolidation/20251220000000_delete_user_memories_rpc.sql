-- Delete user memories atomically (service_role only).
-- Uses a single transaction via PL/pgSQL function execution.

-- NOTE: Supabase CLI can restore `supabase_migrations.schema_migrations` from a cached local backup.
-- If the tracking row for this migration already exists, the CLI will fail at the end when recording
-- the migration version. Make the migration idempotent by deleting any pre-existing row (when present).
DO $do$
BEGIN
  IF to_regclass('supabase_migrations.schema_migrations') IS NOT NULL THEN
    DELETE FROM supabase_migrations.schema_migrations WHERE version = '20251220000000';
  END IF;
END;
$do$;

CREATE OR REPLACE FUNCTION public.delete_user_memories(
  p_user_id UUID
) RETURNS TABLE (
  deleted_turns BIGINT,
  deleted_sessions BIGINT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_deleted_turns BIGINT;
  v_deleted_sessions BIGINT;
BEGIN
  IF coalesce((current_setting('request.jwt.claims', true)::json->>'role'),'') <> 'service_role' THEN
    RAISE EXCEPTION 'Must be called as service role';
  END IF;

  DELETE FROM memories.turns WHERE user_id = p_user_id;
  GET DIAGNOSTICS v_deleted_turns = ROW_COUNT;

  DELETE FROM memories.sessions WHERE user_id = p_user_id;
  GET DIAGNOSTICS v_deleted_sessions = ROW_COUNT;

  RETURN QUERY SELECT v_deleted_turns, v_deleted_sessions;
END;
$$;
