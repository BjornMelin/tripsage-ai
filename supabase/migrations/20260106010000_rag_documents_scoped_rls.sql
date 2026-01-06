-- RAG documents: add user/trip scoping + tighten RLS policies
-- Generated: 2026-01-06
--
-- Goals:
-- - Allow authenticated users to index documents under RLS (no service-role bypass).
-- - Keep global documents readable to authenticated users.
-- - Scope user-authored documents to the owning user (and optionally trip collaborators).

BEGIN;

ALTER TABLE public.rag_documents
  ADD COLUMN IF NOT EXISTS user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS trip_id bigint REFERENCES public.trips(id) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS chat_id uuid REFERENCES public.chat_sessions(id) ON DELETE SET NULL;

DO $do$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'rag_documents_trip_requires_user_check'
      AND conrelid = to_regclass('public.rag_documents')
  ) THEN
    -- NOTE: Added NOT VALID to avoid validating existing rows during deploy (rag_documents can
    -- grow large). A follow-up maintenance migration should backfill any existing trip-scoped
    -- rows missing user_id (e.g. from chat_sessions via chat_id, or legacy metadata), then
    -- validate:
    --
    --   ALTER TABLE public.rag_documents
    --     VALIDATE CONSTRAINT rag_documents_trip_requires_user_check;
    ALTER TABLE public.rag_documents
      ADD CONSTRAINT rag_documents_trip_requires_user_check
      CHECK (trip_id IS NULL OR user_id IS NOT NULL)
      NOT VALID;
  END IF;
END;
$do$;

CREATE INDEX IF NOT EXISTS rag_documents_user_id_idx ON public.rag_documents(user_id);
CREATE INDEX IF NOT EXISTS rag_documents_trip_id_idx ON public.rag_documents(trip_id);
CREATE INDEX IF NOT EXISTS rag_documents_chat_id_idx ON public.rag_documents(chat_id);

-- Trip access helpers (`user_has_trip_access`, `user_has_trip_edit_access`) frequently filter by
-- (trip_id, user_id); a composite index avoids row filtering/bitmap intersections.
-- Note: the trips lookup in these helpers is keyed by the primary key (trips.id) and does not
-- require an additional composite index.
CREATE INDEX IF NOT EXISTS trip_collaborators_trip_user_idx
  ON public.trip_collaborators(trip_id, user_id);

ALTER TABLE public.rag_documents ENABLE ROW LEVEL SECURITY;

-- Drop permissive policies created in 20251211000000_create_rag_documents.sql.
DROP POLICY IF EXISTS "Allow authenticated users to read RAG documents" ON public.rag_documents;
DROP POLICY IF EXISTS "Allow anonymous users to read RAG documents" ON public.rag_documents;
DROP POLICY IF EXISTS "Allow service role to manage RAG documents" ON public.rag_documents;

-- Read:
-- - Global docs (user_id IS NULL) are readable to all authenticated users.
-- - User-owned docs (user_id = auth.uid()) are readable by the owner.
-- - Trip-scoped docs are readable by any user with trip access.
DROP POLICY IF EXISTS rag_documents_select_authenticated ON public.rag_documents;
CREATE POLICY rag_documents_select_authenticated
  ON public.rag_documents
  FOR SELECT
  TO authenticated
  USING (
    -- Only treat NULL user_id rows as global for explicitly-known public namespaces.
    -- This prevents legacy user_content rows (created before user_id existed) from becoming
    -- readable to any authenticated user, and avoids future namespace additions becoming
    -- globally readable by accident.
    (
      user_id IS NULL
      AND namespace IN ('default', 'accommodations', 'destinations', 'activities', 'travel_tips')
    )
    OR user_id = (select auth.uid())
    OR (
      trip_id IS NOT NULL
      AND public.user_has_trip_access((select auth.uid()), trip_id)
    )
  );

-- Write (authenticated):
-- - Only the owner can write.
-- - If trip-scoped, require trip edit access.
-- - If chat-scoped, require the chat session is owned by the caller.
DROP POLICY IF EXISTS rag_documents_insert_authenticated ON public.rag_documents;
CREATE POLICY rag_documents_insert_authenticated
  ON public.rag_documents
  FOR INSERT
  TO authenticated
  WITH CHECK (
    user_id = (select auth.uid())
    AND (
      trip_id IS NULL
      OR public.user_has_trip_edit_access((select auth.uid()), trip_id)
    )
    AND (
      chat_id IS NULL
      OR EXISTS (
        SELECT 1
        FROM public.chat_sessions cs
        WHERE cs.id = chat_id
          AND cs.user_id = (select auth.uid())
      )
    )
  );

DROP POLICY IF EXISTS rag_documents_update_authenticated ON public.rag_documents;
CREATE POLICY rag_documents_update_authenticated
  ON public.rag_documents
  FOR UPDATE
  TO authenticated
  USING (
    user_id = (select auth.uid())
    AND (
      trip_id IS NULL
      OR public.user_has_trip_edit_access((select auth.uid()), trip_id)
    )
    AND (
      chat_id IS NULL
      OR EXISTS (
        SELECT 1
        FROM public.chat_sessions cs
        WHERE cs.id = chat_id
          AND cs.user_id = (select auth.uid())
      )
    )
  )
  WITH CHECK (
    user_id = (select auth.uid())
    AND (
      trip_id IS NULL
      OR public.user_has_trip_edit_access((select auth.uid()), trip_id)
    )
    AND (
      chat_id IS NULL
      OR EXISTS (
        SELECT 1
        FROM public.chat_sessions cs
        WHERE cs.id = chat_id
          AND cs.user_id = (select auth.uid())
      )
    )
  );

DROP POLICY IF EXISTS rag_documents_delete_authenticated ON public.rag_documents;
CREATE POLICY rag_documents_delete_authenticated
  ON public.rag_documents
  FOR DELETE
  TO authenticated
  USING (
    user_id = (select auth.uid())
    AND (
      trip_id IS NULL
      OR public.user_has_trip_edit_access((select auth.uid()), trip_id)
    )
  );

-- Service role retains full access for background indexing/maintenance.
DROP POLICY IF EXISTS rag_documents_service_all ON public.rag_documents;
CREATE POLICY rag_documents_service_all
  ON public.rag_documents
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

COMMIT;
