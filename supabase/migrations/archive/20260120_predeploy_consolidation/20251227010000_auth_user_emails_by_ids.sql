-- Lookup auth user emails by ids (service-role only).
-- This avoids N+1 Admin getUserById calls when listing collaborators.

-- NOTE: Supabase CLI can restore `supabase_migrations.schema_migrations` from a cached local backup.
-- If the tracking row for this migration already exists, the CLI will fail at the end when recording
-- the migration version. Make the migration idempotent by deleting any pre-existing row (when present).
DO $do$
BEGIN
  IF to_regclass('supabase_migrations.schema_migrations') IS NOT NULL THEN
    DELETE FROM supabase_migrations.schema_migrations WHERE version = '20251227010000';
  END IF;
END;
$do$;

CREATE OR REPLACE FUNCTION public.auth_user_emails_by_ids(p_user_ids UUID[])
RETURNS TABLE (user_id UUID, email TEXT)
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = auth, public, pg_temp
AS $$
  SELECT u.id, u.email
  FROM auth.users u
  WHERE u.id = ANY (p_user_ids);
$$;

REVOKE ALL ON FUNCTION public.auth_user_emails_by_ids(UUID[]) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.auth_user_emails_by_ids(UUID[]) TO service_role;
