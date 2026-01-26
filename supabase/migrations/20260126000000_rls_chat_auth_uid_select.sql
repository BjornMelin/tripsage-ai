-- Align chat RLS policies with auth.uid() performance recommendations.

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
