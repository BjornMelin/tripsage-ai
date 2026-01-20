-- Attachments: metadata-first uploads + trip-collaboration reads
-- Generated: 2026-01-06
--
-- Goals:
-- - Prevent direct Storage uploads unless a corresponding file_attachments record exists.
-- - Enforce trip edit access when inserting trip-scoped attachments.
-- - Allow trip collaborators to read trip-scoped attachments via metadata.

-- NOTE: Supabase CLI can restore `supabase_migrations.schema_migrations` from a cached local backup.
-- If the tracking row for this migration already exists, the CLI will fail at the end when recording
-- the migration version. Make the migration idempotent by deleting any pre-existing row (when present).
DO $do$
BEGIN
  IF to_regclass('supabase_migrations.schema_migrations') IS NOT NULL THEN
    DELETE FROM supabase_migrations.schema_migrations WHERE version = '20260106011000';
  END IF;
END;
$do$;

BEGIN;

ALTER TABLE public.file_attachments
  ADD COLUMN IF NOT EXISTS chat_id uuid REFERENCES public.chat_sessions(id) ON DELETE SET NULL;

ALTER TABLE public.file_attachments ENABLE ROW LEVEL SECURITY;

-- Replace overly-broad owner policy created in base schema.
DROP POLICY IF EXISTS file_attachments_owner ON public.file_attachments;

-- Read: owner OR trip collaborator when trip-scoped.
DROP POLICY IF EXISTS file_attachments_select_access ON public.file_attachments;
CREATE POLICY file_attachments_select_access
  ON public.file_attachments
  FOR SELECT
  TO authenticated
  USING (
    user_id = (select auth.uid())
    OR (
      trip_id IS NOT NULL
      AND public.user_has_trip_access((select auth.uid()), trip_id)
    )
  );

-- Write: owner only. If trip-scoped, require trip edit access.
-- If chat_id is set, require the chat session is owned by the caller.
-- If chat_message_id is set, require the message is owned by the caller.
-- NOTE: The `chat_sessions.id` and `chat_messages.id` lookups are backed by their PRIMARY KEY indexes.
DROP POLICY IF EXISTS file_attachments_insert_owner ON public.file_attachments;
CREATE POLICY file_attachments_insert_owner
  ON public.file_attachments
  FOR INSERT
  TO authenticated
  WITH CHECK (
    user_id = (select auth.uid())
    -- Enforce canonical path prefix to prevent path-based auth confusion in Storage RLS policies.
    -- Supports legacy `chat/{userId}/...` paths while enforcing a stable user-owned prefix.
    AND (
      split_part(file_path, '/', 1) = (select auth.uid())::text
      OR (
        split_part(file_path, '/', 1) = 'chat'
        AND split_part(file_path, '/', 2) = (select auth.uid())::text
      )
    )
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
    AND (
      chat_message_id IS NULL
      OR EXISTS (
        SELECT 1
        FROM public.chat_messages cm
        WHERE cm.id = chat_message_id
          AND cm.user_id = (select auth.uid())
      )
    )
  );

DROP POLICY IF EXISTS file_attachments_update_owner ON public.file_attachments;
CREATE POLICY file_attachments_update_owner
  ON public.file_attachments
  FOR UPDATE
  TO authenticated
  USING (user_id = (select auth.uid()))
  WITH CHECK (
    user_id = (select auth.uid())
    -- Keep file_path anchored to the authenticated user's prefix (defense-in-depth).
    AND (
      split_part(file_path, '/', 1) = (select auth.uid())::text
      OR (
        split_part(file_path, '/', 1) = 'chat'
        AND split_part(file_path, '/', 2) = (select auth.uid())::text
      )
    )
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
    AND (
      chat_message_id IS NULL
      OR EXISTS (
        SELECT 1
        FROM public.chat_messages cm
        WHERE cm.id = chat_message_id
          AND cm.user_id = (select auth.uid())
      )
    )
  );

DROP POLICY IF EXISTS file_attachments_delete_owner ON public.file_attachments;
CREATE POLICY file_attachments_delete_owner
  ON public.file_attachments
  FOR DELETE
  TO authenticated
  USING (user_id = (select auth.uid()));

-- =======================================
-- METADATA INVARIANTS (DEFENSE IN DEPTH)
-- =======================================
--
-- Storage RLS policies authorize object UPDATE/DELETE by checking for a matching
-- metadata record (file_path = storage.objects.name). If a user could mutate
-- file_path on an existing metadata row, they could repoint it to another
-- object path and gain authorization. Prevent this by making file_path (and
-- other identity fields) immutable for normal requests.
--
-- Notes:
-- - Allow postgres (migrations) and service_role (admin maintenance) to update.
-- - Do not block updating upload_status or attaching chat_message_id; only block
--   changing identifying fields.
CREATE OR REPLACE FUNCTION public.prevent_file_attachments_identity_change()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  -- Allow migrations and admin maintenance.
  -- PostgREST requests commonly use SET ROLE; session_user remains the connection user.
  -- Use session_user for migrations and auth.role() for service-role maintenance.
  IF session_user IN ('postgres', 'supabase_admin') OR auth.role() = 'service_role' THEN
    RETURN NEW;
  END IF;

  IF NEW.file_path IS DISTINCT FROM OLD.file_path THEN
    RAISE EXCEPTION 'file_path cannot be modified';
  END IF;
  IF NEW.user_id IS DISTINCT FROM OLD.user_id THEN
    RAISE EXCEPTION 'user_id cannot be modified';
  END IF;
  IF NEW.bucket_name IS DISTINCT FROM OLD.bucket_name THEN
    RAISE EXCEPTION 'bucket_name cannot be modified';
  END IF;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS file_attachments_prevent_identity_change ON public.file_attachments;
CREATE TRIGGER file_attachments_prevent_identity_change
  BEFORE UPDATE ON public.file_attachments
  FOR EACH ROW EXECUTE FUNCTION public.prevent_file_attachments_identity_change();

-- Ensure service role policy exists (base schema installs this).
DROP POLICY IF EXISTS file_attachments_service ON public.file_attachments;
CREATE POLICY file_attachments_service
  ON public.file_attachments
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ===========================
-- STORAGE: ATTACHMENTS BUCKET
-- ===========================

-- Replace path-based policies with metadata-backed policies.
DROP POLICY IF EXISTS "Users can upload attachments to their trips" ON storage.objects;
DROP POLICY IF EXISTS "Users can view attachments from accessible trips" ON storage.objects;
DROP POLICY IF EXISTS "Users can view attachments they own by record" ON storage.objects;
DROP POLICY IF EXISTS "Users can update their own attachments" ON storage.objects;
DROP POLICY IF EXISTS "Users can delete their own attachments" ON storage.objects;

DROP POLICY IF EXISTS attachments_insert_by_record ON storage.objects;
CREATE POLICY attachments_insert_by_record
  ON storage.objects
  FOR INSERT
  TO authenticated
  WITH CHECK (
    bucket_id = 'attachments'
    AND EXISTS (
      SELECT 1
      FROM public.file_attachments fa
      WHERE fa.file_path = name
        AND fa.user_id = (select auth.uid())
        AND fa.upload_status = 'uploading'
        -- NOTE: Stale `uploading` records are blocked from authorizing uploads after 15 minutes;
        -- cleanup is intentionally handled out-of-band (e.g. scheduled maintenance) to avoid requiring pg_cron.
        AND fa.created_at > (now() - interval '15 minutes')
    )
  );

DROP POLICY IF EXISTS attachments_select_by_record ON storage.objects;
CREATE POLICY attachments_select_by_record
  ON storage.objects
  FOR SELECT
  TO authenticated
  USING (
    bucket_id = 'attachments'
    AND EXISTS (
      SELECT 1
      FROM public.file_attachments fa
      WHERE fa.file_path = name
        AND (
          fa.user_id = (select auth.uid())
          OR (
            fa.trip_id IS NOT NULL
            AND public.user_has_trip_access((select auth.uid()), fa.trip_id)
          )
        )
    )
  );

DROP POLICY IF EXISTS attachments_update_by_record_owner ON storage.objects;
CREATE POLICY attachments_update_by_record_owner
  ON storage.objects
  FOR UPDATE
  TO authenticated
  USING (
    bucket_id = 'attachments'
    AND EXISTS (
      SELECT 1
      FROM public.file_attachments fa
      WHERE fa.file_path = name
        AND fa.user_id = (select auth.uid())
    )
  )
  WITH CHECK (
    bucket_id = 'attachments'
    AND EXISTS (
      SELECT 1
      FROM public.file_attachments fa
      WHERE fa.file_path = name
        AND fa.user_id = (select auth.uid())
    )
  );

DROP POLICY IF EXISTS attachments_delete_by_record_owner ON storage.objects;
CREATE POLICY attachments_delete_by_record_owner
  ON storage.objects
  FOR DELETE
  TO authenticated
  USING (
    bucket_id = 'attachments'
    AND EXISTS (
      SELECT 1
      FROM public.file_attachments fa
      WHERE fa.file_path = name
        AND fa.user_id = (select auth.uid())
    )
  );

COMMIT;
