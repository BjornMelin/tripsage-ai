-- Trip collaboration RLS hardening + shared trip access
-- Generated: 2025-12-27
--
-- Goals:
-- - Prevent insecure self-inserts into public.trip_collaborators
-- - Enable trip owners and collaborators to read trips
-- - Enable editor/admin collaborators to update trips (owner always allowed)
-- - Keep policies non-recursive via SECURITY DEFINER helpers

-- ===========================
-- HELPERS
-- ===========================

-- Owner predicate (SECURITY DEFINER to avoid RLS recursion)
CREATE OR REPLACE FUNCTION public.user_is_trip_owner(p_user_id UUID, p_trip_id BIGINT)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public, pg_temp
AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1
    FROM public.trips t
    WHERE t.id = p_trip_id
      AND t.user_id = p_user_id
  );
END;
$$;

-- Edit predicate: owner OR collaborator with role editor/admin (SECURITY DEFINER to avoid RLS recursion)
CREATE OR REPLACE FUNCTION public.user_has_trip_edit_access(p_user_id UUID, p_trip_id BIGINT)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public, pg_temp
AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1
    FROM public.trips t
    WHERE t.id = p_trip_id
      AND t.user_id = p_user_id
    UNION
    SELECT 1
    FROM public.trip_collaborators tc
    WHERE tc.trip_id = p_trip_id
      AND tc.user_id = p_user_id
      AND tc.role IN ('editor', 'admin')
  );
END;
$$;

-- Lookup auth user id by email (service-role only).
-- This avoids scanning the Admin listUsers API when inviting collaborators.
CREATE OR REPLACE FUNCTION public.auth_user_id_by_email(p_email TEXT)
RETURNS UUID
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = auth, public, pg_temp
AS $$
  SELECT u.id
  FROM auth.users u
  WHERE lower(u.email) = lower(p_email)
  LIMIT 1;
$$;

REVOKE ALL ON FUNCTION public.auth_user_id_by_email(TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.auth_user_id_by_email(TEXT) TO service_role;

-- ===========================
-- TRIP COLLABORATORS
-- ===========================

-- Ensure role values stay within supported tiers.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'trip_collaborators_role_check'
      AND conrelid = 'public.trip_collaborators'::regclass
  ) THEN
    ALTER TABLE public.trip_collaborators
      ADD CONSTRAINT trip_collaborators_role_check
      CHECK (role IN ('viewer', 'editor', 'admin'));
  END IF;
END;
$$;

ALTER TABLE public.trip_collaborators ENABLE ROW LEVEL SECURITY;

-- Drop insecure base policies (allowed any user to self-add as collaborator).
DROP POLICY IF EXISTS trip_collab_select ON public.trip_collaborators;
DROP POLICY IF EXISTS trip_collab_insert ON public.trip_collaborators;

-- Read: any user with access to the trip can see collaborator rows.
-- Uses SECURITY DEFINER helper from base schema (`public.user_has_trip_access`).
DROP POLICY IF EXISTS trip_collaborators_select_trip_members ON public.trip_collaborators;
CREATE POLICY trip_collaborators_select_trip_members
  ON public.trip_collaborators
  FOR SELECT
  TO authenticated
  USING (public.user_has_trip_access(auth.uid(), trip_id));

-- Write: only trip owners can add/update collaborator roles.
DROP POLICY IF EXISTS trip_collaborators_insert_owner ON public.trip_collaborators;
CREATE POLICY trip_collaborators_insert_owner
  ON public.trip_collaborators
  FOR INSERT
  TO authenticated
  WITH CHECK (public.user_is_trip_owner(auth.uid(), trip_id));

DROP POLICY IF EXISTS trip_collaborators_update_owner ON public.trip_collaborators;
CREATE POLICY trip_collaborators_update_owner
  ON public.trip_collaborators
  FOR UPDATE
  TO authenticated
  USING (public.user_is_trip_owner(auth.uid(), trip_id))
  WITH CHECK (public.user_is_trip_owner(auth.uid(), trip_id));

-- Delete: owner can remove anyone; collaborators can remove themselves (leave trip).
DROP POLICY IF EXISTS trip_collaborators_delete_owner_or_self ON public.trip_collaborators;
CREATE POLICY trip_collaborators_delete_owner_or_self
  ON public.trip_collaborators
  FOR DELETE
  TO authenticated
  USING (public.user_is_trip_owner(auth.uid(), trip_id) OR user_id = auth.uid());

-- ===========================
-- TRIPS
-- ===========================

ALTER TABLE public.trips ENABLE ROW LEVEL SECURITY;

-- Read trips for collaborators.
DROP POLICY IF EXISTS trips_select_accessible ON public.trips;
CREATE POLICY trips_select_accessible
  ON public.trips
  FOR SELECT
  TO authenticated
  USING (public.user_has_trip_access(auth.uid(), id));

-- Allow editor/admin collaborators to update trips.
DROP POLICY IF EXISTS trips_update_collaborators ON public.trips;
CREATE POLICY trips_update_collaborators
  ON public.trips
  FOR UPDATE
  TO authenticated
  USING (public.user_has_trip_edit_access(auth.uid(), id))
  WITH CHECK (public.user_has_trip_edit_access(auth.uid(), id));

-- ===========================
-- REALTIME (BROADCAST / PRESENCE)
-- ===========================

-- Authorize private `trip:{trip_id}` channels for trip owners + collaborators.
-- This powers ephemeral collaboration activity events via Realtime Broadcast.
DO $do$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'realtime'
      AND table_name = 'messages'
  ) THEN
    EXECUTE 'ALTER TABLE realtime.messages ENABLE ROW LEVEL SECURITY';

    IF NOT EXISTS (
      SELECT 1
      FROM pg_policies
      WHERE schemaname = 'realtime'
        AND tablename = 'messages'
        AND policyname = 'rtm_trip_topic_read'
    ) THEN
      EXECUTE $pol$
        CREATE POLICY "rtm_trip_topic_read"
        ON realtime.messages
        FOR SELECT
        TO authenticated
	        USING (
	          realtime.topic() ~ '^trip:[0-9]+$'
	          AND public.user_has_trip_access(auth.uid(), (public.rt_topic_suffix())::bigint)
	          AND realtime.messages.extension IN ('broadcast', 'presence')
	        )
	      $pol$;
	    END IF;

    IF NOT EXISTS (
      SELECT 1
      FROM pg_policies
      WHERE schemaname = 'realtime'
        AND tablename = 'messages'
        AND policyname = 'rtm_trip_topic_write'
    ) THEN
      EXECUTE $pol$
        CREATE POLICY "rtm_trip_topic_write"
        ON realtime.messages
        FOR INSERT
        TO authenticated
	        WITH CHECK (
	          realtime.topic() ~ '^trip:[0-9]+$'
	          AND public.user_has_trip_access(auth.uid(), (public.rt_topic_suffix())::bigint)
	          AND realtime.messages.extension IN ('broadcast', 'presence')
	        )
	      $pol$;
	    END IF;
	  END IF;
END $do$;
