-- Saved places (trip-scoped POIs with RLS)
-- Generated: 2026-01-07
--
-- Goals:
-- - Persist user-saved places to trips without storing raw provider payloads.
-- - Enforce trip collaboration access via existing SECURITY DEFINER helpers.

BEGIN;

-- NOTE: Supabase CLI can restore `supabase_migrations.schema_migrations` from a cached local backup.
-- If the tracking row for this migration already exists, the CLI will fail at the end when recording
-- the migration version. Make the migration idempotent by deleting any pre-existing row (when present).
DO $do$
BEGIN
  IF to_regclass('supabase_migrations.schema_migrations') IS NOT NULL THEN
    DELETE FROM supabase_migrations.schema_migrations WHERE version = '20260107002000';
  END IF;
END;
$do$;

CREATE TABLE IF NOT EXISTS public.saved_places (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  trip_id BIGINT NOT NULL REFERENCES public.trips(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  provider TEXT NOT NULL DEFAULT 'googleplaces',
  place_id TEXT NOT NULL,
  place_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT saved_places_place_id_check CHECK (length(place_id) > 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS saved_places_trip_place_unique
  ON public.saved_places (trip_id, place_id);

CREATE INDEX IF NOT EXISTS saved_places_trip_idx
  ON public.saved_places (trip_id);

CREATE INDEX IF NOT EXISTS saved_places_user_idx
  ON public.saved_places (user_id);

ALTER TABLE public.saved_places ENABLE ROW LEVEL SECURITY;

-- Read: any user with access to the trip may read saved places.
DROP POLICY IF EXISTS saved_places_select_trip_access ON public.saved_places;
CREATE POLICY saved_places_select_trip_access
  ON public.saved_places
  FOR SELECT
  TO authenticated
  USING (public.user_has_trip_access((select auth.uid()), trip_id));

-- Write: only editors/admins (and owners) may add/update/delete saved places.
DROP POLICY IF EXISTS saved_places_insert_trip_edit ON public.saved_places;
CREATE POLICY saved_places_insert_trip_edit
  ON public.saved_places
  FOR INSERT
  TO authenticated
  WITH CHECK (
    user_id = (select auth.uid())
    AND public.user_has_trip_edit_access((select auth.uid()), trip_id)
  );

DROP POLICY IF EXISTS saved_places_update_trip_edit ON public.saved_places;
CREATE POLICY saved_places_update_trip_edit
  ON public.saved_places
  FOR UPDATE
  TO authenticated
  USING (public.user_has_trip_edit_access((select auth.uid()), trip_id))
  WITH CHECK (public.user_has_trip_edit_access((select auth.uid()), trip_id));

DROP POLICY IF EXISTS saved_places_delete_trip_edit ON public.saved_places;
CREATE POLICY saved_places_delete_trip_edit
  ON public.saved_places
  FOR DELETE
  TO authenticated
  USING (public.user_has_trip_edit_access((select auth.uid()), trip_id));

-- Service role: full access.
DROP POLICY IF EXISTS saved_places_service_all ON public.saved_places;
CREATE POLICY saved_places_service_all
  ON public.saved_places
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- updated_at trigger (reuses base schema helper).
DO $$
BEGIN
  PERFORM 1 FROM pg_trigger WHERE tgname = 'trg_saved_places_updated_at';
  IF NOT FOUND THEN
    CREATE TRIGGER trg_saved_places_updated_at BEFORE UPDATE ON public.saved_places
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
  END IF;
END $$;

-- Prevent collaborators from reassigning identity columns.
CREATE OR REPLACE FUNCTION public.prevent_saved_places_identity_change()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.user_id IS DISTINCT FROM OLD.user_id THEN
    RAISE EXCEPTION 'user_id cannot be modified';
  END IF;
  IF NEW.trip_id IS DISTINCT FROM OLD.trip_id THEN
    RAISE EXCEPTION 'trip_id cannot be modified';
  END IF;
  IF NEW.place_id IS DISTINCT FROM OLD.place_id THEN
    RAISE EXCEPTION 'place_id cannot be modified';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS saved_places_prevent_identity_change ON public.saved_places;
CREATE TRIGGER saved_places_prevent_identity_change
  BEFORE UPDATE ON public.saved_places
  FOR EACH ROW EXECUTE FUNCTION public.prevent_saved_places_identity_change();

COMMIT;
