-- RLS hardening: chat sessions + itinerary collaboration + attachment storage path support
-- Generated: 2026-01-06
--
-- Goals:
-- - Ensure chat session DELETE works under RLS (owner-only).
-- - Ensure chat session INSERT validates trip access when trip_id is set.
-- - Allow trip collaborators to read itinerary items and editors/admins to mutate them.
-- - Allow attachment uploads using the current API path prefix (chat/{userId}/...).

-- ===========================
-- CHAT SESSIONS
-- ===========================

ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;

-- Tighten insert policy to require trip access when trip_id is set.
DROP POLICY IF EXISTS chat_sessions_insert ON public.chat_sessions;
CREATE POLICY chat_sessions_insert
  ON public.chat_sessions
  FOR INSERT
  TO authenticated
  WITH CHECK (
    user_id = (select auth.uid())
    AND (
      trip_id IS NULL
      OR public.user_has_trip_access((select auth.uid()), trip_id)
    )
  );

-- Add missing policies required by DELETE /api/chat/sessions/:id.
DROP POLICY IF EXISTS chat_sessions_update_owner ON public.chat_sessions;
CREATE POLICY chat_sessions_update_owner
  ON public.chat_sessions
  FOR UPDATE
  TO authenticated
  USING (user_id = (select auth.uid()))
  WITH CHECK (user_id = (select auth.uid()));

DROP POLICY IF EXISTS chat_sessions_delete_owner ON public.chat_sessions;
CREATE POLICY chat_sessions_delete_owner
  ON public.chat_sessions
  FOR DELETE
  TO authenticated
  USING (user_id = (select auth.uid()));

-- ===========================
-- ITINERARY ITEMS
-- ===========================

ALTER TABLE public.itinerary_items ENABLE ROW LEVEL SECURITY;

-- Replace owner-only policies with trip-collaboration policies.
DROP POLICY IF EXISTS itinerary_select_own ON public.itinerary_items;
DROP POLICY IF EXISTS itinerary_insert_own ON public.itinerary_items;
DROP POLICY IF EXISTS itinerary_update_own ON public.itinerary_items;
DROP POLICY IF EXISTS itinerary_delete_trip_edit ON public.itinerary_items;

CREATE POLICY itinerary_select_trip_access
  ON public.itinerary_items
  FOR SELECT
  TO authenticated
  USING (public.user_has_trip_access((select auth.uid()), trip_id));

CREATE POLICY itinerary_insert_trip_edit
  ON public.itinerary_items
  FOR INSERT
  TO authenticated
  WITH CHECK (
    user_id = (select auth.uid())
    AND public.user_has_trip_edit_access((select auth.uid()), trip_id)
  );

CREATE POLICY itinerary_update_trip_edit
  ON public.itinerary_items
  FOR UPDATE
  TO authenticated
  USING (public.user_has_trip_edit_access((select auth.uid()), trip_id))
  WITH CHECK (public.user_has_trip_edit_access((select auth.uid()), trip_id));

CREATE POLICY itinerary_delete_trip_edit
  ON public.itinerary_items
  FOR DELETE
  TO authenticated
  USING (public.user_has_trip_edit_access((select auth.uid()), trip_id));

-- Prevent collaborators from reassigning ownership by mutating user_id.
CREATE OR REPLACE FUNCTION public.prevent_itinerary_user_id_change()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.user_id IS DISTINCT FROM OLD.user_id THEN
    RAISE EXCEPTION 'user_id cannot be modified';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS itinerary_items_prevent_user_id_change ON public.itinerary_items;
CREATE TRIGGER itinerary_items_prevent_user_id_change
  BEFORE UPDATE ON public.itinerary_items
  FOR EACH ROW EXECUTE FUNCTION public.prevent_itinerary_user_id_change();

-- ===========================
-- STORAGE: ATTACHMENTS BUCKET
-- ===========================

-- Allow uploads for the current attachment path used by /api/chat/attachments:
-- `{userId}/{...}`
DROP POLICY IF EXISTS "Users can upload attachments to their trips" ON storage.objects;
CREATE POLICY "Users can upload attachments to their trips"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (
  bucket_id = 'attachments'
  AND split_part(name, '/', 1) = (select auth.uid())::text
);
