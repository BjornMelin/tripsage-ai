-- Trips: relax budget constraint to allow 0 (unknown budget)
-- Generated: 2026-01-07

-- NOTE: Supabase CLI can restore `supabase_migrations.schema_migrations` from a cached local backup.
-- If the tracking row for this migration already exists, the CLI will fail at the end when recording
-- the migration version. Make the migration idempotent by deleting any pre-existing row (when present).
DO $do$
BEGIN
  IF to_regclass('supabase_migrations.schema_migrations') IS NOT NULL THEN
    DELETE FROM supabase_migrations.schema_migrations WHERE version = '20260107000000';
  END IF;
END;
$do$;

ALTER TABLE public.trips
  DROP CONSTRAINT IF EXISTS trips_budget_check;

UPDATE public.trips
SET budget = 0
WHERE budget < 0;

ALTER TABLE public.trips
  ADD CONSTRAINT trips_budget_check CHECK (budget >= 0) NOT VALID;

ALTER TABLE public.trips
  VALIDATE CONSTRAINT trips_budget_check;

ALTER TABLE public.trips
  ALTER COLUMN budget SET DEFAULT 0;
