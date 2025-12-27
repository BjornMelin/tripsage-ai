-- Adds Supabase Realtime Authorization policies for existing topic patterns.
-- Keeps policies idempotent and scoped to known topics used by the app.
--
-- IMPORTANT:
-- - RLS policy expressions must be exception-free. Unsafe casts in RLS can break Realtime joins.
-- - This migration introduces NULL-safe casting helpers and hardens existing helpers accordingly.
--
-- Topics:
-- - user:{uuid}    (per-user broadcast/presence)
-- - session:{uuid} (chat broadcast/presence)
-- - trip:{id}      (trip collaboration broadcast/presence)
--
-- Note: trip collaboration introduced `trip:{id}` policies in 20251227000000_trip_collaboration.sql.
-- This migration recreates them to remove unsafe casts.

CREATE OR REPLACE FUNCTION public.try_cast_uuid(p_value TEXT)
RETURNS UUID
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
  RETURN p_value::uuid;
EXCEPTION WHEN OTHERS THEN
  RETURN NULL;
END;
$$;

CREATE OR REPLACE FUNCTION public.try_cast_bigint(p_value TEXT)
RETURNS BIGINT
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
  RETURN p_value::bigint;
EXCEPTION WHEN OTHERS THEN
  RETURN NULL;
END;
$$;

-- Hardened version of the base helper so RLS policies can call it safely even if
-- `realtime.topic()` does not match the expected `session:{uuid}` format.
CREATE OR REPLACE FUNCTION public.rt_is_session_member()
RETURNS boolean
LANGUAGE plpgsql
STABLE AS $$
DECLARE ok boolean := false;
DECLARE session_id uuid;
BEGIN
  IF to_regclass('public.chat_sessions') IS NULL THEN
    RETURN false;
  END IF;

  session_id := public.try_cast_uuid(public.rt_topic_suffix());
  IF session_id IS NULL THEN
    RETURN false;
  END IF;

  EXECUTE '
    SELECT EXISTS (
      SELECT 1
      FROM public.chat_sessions cs
      LEFT JOIN public.trips t ON t.id = cs.trip_id
      LEFT JOIN public.trip_collaborators tc ON tc.trip_id = cs.trip_id AND tc.user_id = auth.uid()
      WHERE cs.id = $1
        AND (cs.user_id = auth.uid() OR t.user_id = auth.uid() OR tc.user_id IS NOT NULL)
    )'
    INTO ok
    USING session_id;

  RETURN ok;
END;
$$;

DO $do$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'realtime'
      AND table_name = 'messages'
  ) THEN
    EXECUTE 'ALTER TABLE realtime.messages ENABLE ROW LEVEL SECURITY';

    -- Recreate trip:{id} policies with NULL-safe casting to avoid RLS exceptions.
    EXECUTE 'DROP POLICY IF EXISTS "rtm_trip_topic_read" ON realtime.messages';
    EXECUTE 'DROP POLICY IF EXISTS "rtm_trip_topic_write" ON realtime.messages';

    EXECUTE $pol$
      CREATE POLICY "rtm_trip_topic_read"
      ON realtime.messages
      FOR SELECT
      TO authenticated
      USING (
        realtime.topic() ~ '^trip:[0-9]+$'
        AND public.user_has_trip_access(auth.uid(), public.try_cast_bigint(public.rt_topic_suffix()))
        AND realtime.messages.extension IN ('broadcast', 'presence')
      )
    $pol$;

    EXECUTE $pol$
      CREATE POLICY "rtm_trip_topic_write"
      ON realtime.messages
      FOR INSERT
      TO authenticated
      WITH CHECK (
        realtime.topic() ~ '^trip:[0-9]+$'
        AND public.user_has_trip_access(auth.uid(), public.try_cast_bigint(public.rt_topic_suffix()))
        AND realtime.messages.extension IN ('broadcast', 'presence')
      )
    $pol$;

    -- user:{uuid}
    IF NOT EXISTS (
      SELECT 1
      FROM pg_policies
      WHERE schemaname = 'realtime'
        AND tablename = 'messages'
        AND policyname = 'rtm_user_topic_read'
    ) THEN
      EXECUTE $pol$
        CREATE POLICY "rtm_user_topic_read"
        ON realtime.messages
        FOR SELECT
        TO authenticated
        USING (
          realtime.topic() ~* '^user:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
          AND public.rt_topic_suffix() = auth.uid()::text
          AND realtime.messages.extension IN ('broadcast', 'presence')
        )
      $pol$;
    END IF;

    IF NOT EXISTS (
      SELECT 1
      FROM pg_policies
      WHERE schemaname = 'realtime'
        AND tablename = 'messages'
        AND policyname = 'rtm_user_topic_write'
    ) THEN
      EXECUTE $pol$
        CREATE POLICY "rtm_user_topic_write"
        ON realtime.messages
        FOR INSERT
        TO authenticated
        WITH CHECK (
          realtime.topic() ~* '^user:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
          AND public.rt_topic_suffix() = auth.uid()::text
          AND realtime.messages.extension IN ('broadcast', 'presence')
        )
      $pol$;
    END IF;

    -- session:{uuid}
    IF EXISTS (
      SELECT 1
      FROM information_schema.tables
      WHERE table_schema = 'public'
        AND table_name = 'chat_sessions'
    ) THEN
      IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'realtime'
          AND tablename = 'messages'
          AND policyname = 'rtm_session_topic_read'
      ) THEN
        EXECUTE $pol$
          CREATE POLICY "rtm_session_topic_read"
          ON realtime.messages
          FOR SELECT
          TO authenticated
          USING (
            realtime.topic() ~* '^session:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            AND public.rt_is_session_member()
            AND realtime.messages.extension IN ('broadcast', 'presence')
          )
        $pol$;
      END IF;

      IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'realtime'
          AND tablename = 'messages'
          AND policyname = 'rtm_session_topic_write'
      ) THEN
        EXECUTE $pol$
          CREATE POLICY "rtm_session_topic_write"
          ON realtime.messages
          FOR INSERT
          TO authenticated
          WITH CHECK (
            realtime.topic() ~* '^session:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            AND public.rt_is_session_member()
            AND realtime.messages.extension IN ('broadcast', 'presence')
          )
        $pol$;
      END IF;
    END IF;
  END IF;
END $do$;
