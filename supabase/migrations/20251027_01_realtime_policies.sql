-- Realtime Authorization Policies
-- Date: 2025-10-27
-- Purpose: Enforce private channel authorization for Supabase Realtime Broadcast & Presence
-- Strategy:
--   - Use RLS policies on realtime.messages with realtime.topic() and JWT claims
--   - Topics:
--       user:{sub}       -> only the subject user may read/write
--       session:{uuid}   -> session owner or trip collaborators may read/write
--   - Extensions covered: broadcast and presence
--
-- References:
--   - Supabase Docs: Realtime Authorization (Public Beta)
--   - https://supabase.com/docs/guides/realtime/authorization

-- Enable RLS on the Realtime messages table to ensure policies apply
ALTER TABLE IF EXISTS "realtime"."messages" ENABLE ROW LEVEL SECURITY;

-- Helper predicates (inline) used by policies
--  - prefix = split_part(topic, ':', 1)
--  - suffix = split_part(topic, ':', 2)

-- =============================
-- user:{sub} channel policies
-- =============================

-- Allow the subject user to read broadcast/presence on user:{sub}
CREATE POLICY "rtm_user_topic_read"
ON "realtime"."messages"
FOR SELECT
TO authenticated
USING (
  (split_part((SELECT realtime.topic()), ':', 1) = 'user')
  AND (split_part((SELECT realtime.topic()), ':', 2) = auth.uid()::text)
  AND ("realtime"."messages"."extension" IN ('broadcast', 'presence'))
);

-- Allow the subject user to write (broadcast/presence) on user:{sub}
CREATE POLICY "rtm_user_topic_write"
ON "realtime"."messages"
FOR INSERT
TO authenticated
WITH CHECK (
  (split_part((SELECT realtime.topic()), ':', 1) = 'user')
  AND (split_part((SELECT realtime.topic()), ':', 2) = auth.uid()::text)
  AND ("realtime"."messages"."extension" IN ('broadcast', 'presence'))
);

-- =============================
-- session:{uuid} channel policies
-- =============================

-- Read policy: session owner, trip owner, or collaborators can receive
CREATE POLICY "rtm_session_topic_read"
ON "realtime"."messages"
FOR SELECT
TO authenticated
USING (
  (split_part((SELECT realtime.topic()), ':', 1) = 'session')
  AND (
    EXISTS (
      SELECT 1
      FROM public.chat_sessions cs
      LEFT JOIN public.trips t ON t.id = cs.trip_id
      LEFT JOIN public.trip_collaborators tc
        ON tc.trip_id = cs.trip_id
       AND tc.user_id = auth.uid()
      WHERE cs.id = (split_part((SELECT realtime.topic()), ':', 2))::uuid
        AND (
          cs.user_id = auth.uid()
          OR t.user_id = auth.uid()
          OR tc.user_id IS NOT NULL
        )
    )
  )
  AND ("realtime"."messages"."extension" IN ('broadcast', 'presence'))
);

-- Write policy: session owner, trip owner, or collaborators can send
CREATE POLICY "rtm_session_topic_write"
ON "realtime"."messages"
FOR INSERT
TO authenticated
WITH CHECK (
  (split_part((SELECT realtime.topic()), ':', 1) = 'session')
  AND (
    EXISTS (
      SELECT 1
      FROM public.chat_sessions cs
      LEFT JOIN public.trips t ON t.id = cs.trip_id
      LEFT JOIN public.trip_collaborators tc
        ON tc.trip_id = cs.trip_id
       AND tc.user_id = auth.uid()
      WHERE cs.id = (split_part((SELECT realtime.topic()), ':', 2))::uuid
        AND (
          cs.user_id = auth.uid()
          OR t.user_id = auth.uid()
          OR tc.user_id IS NOT NULL
        )
    )
  )
  AND ("realtime"."messages"."extension" IN ('broadcast', 'presence'))
);

-- Notes:
-- - Realtime evaluates these policies at channel join and on access_token refresh.
-- - Ensure Realtime Settings -> Channel Restrictions = Private (disable public access).
-- - Client code must create channels with { config: { private: true } } and call
--   supabase.realtime.setAuth(access_token) whenever the token changes.

DO $$
BEGIN
  RAISE NOTICE '✅ Realtime authorization policies installed: user:{sub}, session:{uuid} (broadcast/presence)';
END $$;

