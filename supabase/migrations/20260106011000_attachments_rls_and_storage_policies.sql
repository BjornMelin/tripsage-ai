-- Attachments: metadata-first uploads + trip-collaboration reads
-- Generated: 2026-01-06
--
-- Goals:
-- - Prevent direct Storage uploads unless a corresponding file_attachments record exists.
-- - Enforce trip edit access when inserting trip-scoped attachments.
-- - Allow trip collaborators to read trip-scoped attachments via metadata.

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
DROP POLICY IF EXISTS file_attachments_insert_owner ON public.file_attachments;
CREATE POLICY file_attachments_insert_owner
  ON public.file_attachments
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
      OR chat_id IN (
        SELECT id
        FROM public.chat_sessions
        WHERE user_id = (select auth.uid())
      )
    )
    AND (
      chat_message_id IS NULL
      OR chat_message_id IN (
        SELECT id
        FROM public.chat_messages
        WHERE user_id = (select auth.uid())
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
    AND (
      trip_id IS NULL
      OR public.user_has_trip_edit_access((select auth.uid()), trip_id)
    )
    AND (
      chat_id IS NULL
      OR chat_id IN (
        SELECT id
        FROM public.chat_sessions
        WHERE user_id = (select auth.uid())
      )
    )
    AND (
      chat_message_id IS NULL
      OR chat_message_id IN (
        SELECT id
        FROM public.chat_messages
        WHERE user_id = (select auth.uid())
      )
    )
  );

DROP POLICY IF EXISTS file_attachments_delete_owner ON public.file_attachments;
CREATE POLICY file_attachments_delete_owner
  ON public.file_attachments
  FOR DELETE
  TO authenticated
  USING (user_id = (select auth.uid()));

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
