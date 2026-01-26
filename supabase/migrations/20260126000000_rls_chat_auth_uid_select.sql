-- Align chat RLS policies with auth.uid() performance recommendations and add supporting indexes across chat, trips, and auth tables.

DROP POLICY IF EXISTS "chat_messages_select" ON public.chat_messages;
CREATE POLICY chat_messages_select ON public.chat_messages FOR SELECT TO authenticated USING (
  session_id IN (
    SELECT id FROM public.chat_sessions
    WHERE user_id = (select auth.uid())
    OR trip_id IN (
      SELECT id FROM public.trips WHERE user_id = (select auth.uid())
      UNION
      SELECT trip_id FROM public.trip_collaborators WHERE user_id = (select auth.uid())
    )
  )
);

DROP POLICY IF EXISTS "chat_messages_insert" ON public.chat_messages;
CREATE POLICY chat_messages_insert ON public.chat_messages FOR INSERT TO authenticated WITH CHECK (
  user_id = (select auth.uid())
  AND session_id IN (
    SELECT id FROM public.chat_sessions WHERE user_id = (select auth.uid())
  )
);

DROP POLICY IF EXISTS "chat_tool_calls_select" ON public.chat_tool_calls;
CREATE POLICY chat_tool_calls_select ON public.chat_tool_calls FOR SELECT TO authenticated USING (
  message_id IN (
    SELECT cm.id
    FROM public.chat_messages cm
    JOIN public.chat_sessions cs ON cm.session_id = cs.id
    WHERE cs.user_id = (select auth.uid())
    OR cs.trip_id IN (
      SELECT id FROM public.trips WHERE user_id = (select auth.uid())
      UNION
      SELECT trip_id FROM public.trip_collaborators WHERE user_id = (select auth.uid())
    )
  )
);

DROP POLICY IF EXISTS "chat_tool_calls_insert" ON public.chat_tool_calls;
CREATE POLICY chat_tool_calls_insert ON public.chat_tool_calls FOR INSERT TO authenticated WITH CHECK (
  message_id IN (
    SELECT id FROM public.chat_messages WHERE user_id = (select auth.uid())
  )
);

-- Indexes aligned with current query patterns and RLS access paths.
CREATE INDEX IF NOT EXISTS trips_user_status_created_idx
  ON public.trips (user_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS chat_sessions_user_updated_idx
  ON public.chat_sessions (user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS trip_collaborators_user_trip_idx
  ON public.trip_collaborators (user_id, trip_id);
CREATE INDEX IF NOT EXISTS mfa_enrollments_challenge_factor_issued_idx
  ON public.mfa_enrollments (challenge_id, factor_id, issued_at DESC);
CREATE INDEX IF NOT EXISTS auth_backup_codes_active_lookup_idx
  ON public.auth_backup_codes (user_id, code_hash)
  WHERE consumed_at IS NULL;
CREATE INDEX IF NOT EXISTS chat_messages_session_user_id_idx
  ON public.chat_messages (session_id, user_id, id);
CREATE INDEX IF NOT EXISTS chat_tool_calls_message_id_idx
  ON public.chat_tool_calls (message_id);
