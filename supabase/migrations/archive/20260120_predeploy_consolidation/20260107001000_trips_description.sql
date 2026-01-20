-- Description: Add trip description field

-- NOTE: Supabase CLI can restore `supabase_migrations.schema_migrations` from a cached local backup.
-- If the tracking row for this migration already exists, the CLI will fail at the end when recording
-- the migration version. Make the migration idempotent by deleting any pre-existing row (when present).
DO $do$
BEGIN
  IF to_regclass('supabase_migrations.schema_migrations') IS NOT NULL THEN
    DELETE FROM supabase_migrations.schema_migrations WHERE version = '20260107001000';
  END IF;
END;
$do$;

ALTER TABLE public.trips
  ADD COLUMN IF NOT EXISTS description TEXT;
