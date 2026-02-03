-- Optimize RLS policies by wrapping auth.uid() in a SELECT to avoid per-row calls.
-- See: Supabase RLS performance recommendations.

-- ===========================
-- PUBLIC SCHEMA
-- ===========================

-- profiles
DROP POLICY IF EXISTS "Profiles owner select" ON public.profiles;
CREATE POLICY "Profiles owner select" ON public.profiles
  FOR SELECT
  TO authenticated
  USING ((select auth.uid()) = id);

DROP POLICY IF EXISTS "Profiles owner update" ON public.profiles;
CREATE POLICY "Profiles owner update" ON public.profiles
  FOR UPDATE
  TO authenticated
  USING ((select auth.uid()) = id)
  WITH CHECK ((select auth.uid()) = id);

DROP POLICY IF EXISTS "Profiles owner insert" ON public.profiles;
CREATE POLICY "Profiles owner insert" ON public.profiles
  FOR INSERT
  TO authenticated
  WITH CHECK ((select auth.uid()) = id);

-- gateway BYOK keys
DROP POLICY IF EXISTS gateway_user_keys_owner ON public.gateway_user_keys;
CREATE POLICY gateway_user_keys_owner
  ON public.gateway_user_keys
  FOR ALL
  TO authenticated
  USING ((select auth.uid()) = user_id)
  WITH CHECK ((select auth.uid()) = user_id);

-- trips
DROP POLICY IF EXISTS trips_insert_own ON public.trips;
CREATE POLICY trips_insert_own
  ON public.trips
  FOR INSERT
  TO authenticated
  WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS trips_select_accessible ON public.trips;
CREATE POLICY trips_select_accessible
  ON public.trips
  FOR SELECT
  TO authenticated
  USING (public.user_has_trip_access((select auth.uid()), id));

DROP POLICY IF EXISTS trips_update_collaborators ON public.trips;
CREATE POLICY trips_update_collaborators
  ON public.trips
  FOR UPDATE
  TO authenticated
  USING (public.user_has_trip_edit_access((select auth.uid()), id))
  WITH CHECK (public.user_has_trip_edit_access((select auth.uid()), id));

DROP POLICY IF EXISTS trips_delete_own ON public.trips;
CREATE POLICY trips_delete_own
  ON public.trips
  FOR DELETE
  TO authenticated
  USING ((select auth.uid()) = user_id);

-- flights
DROP POLICY IF EXISTS flights_mutate_own ON public.flights;
CREATE POLICY flights_mutate_own
  ON public.flights
  FOR ALL
  TO authenticated
  USING (user_id = (select auth.uid()))
  WITH CHECK (user_id = (select auth.uid()));

-- bookings
DROP POLICY IF EXISTS bookings_select_own ON public.bookings;
CREATE POLICY bookings_select_own
  ON public.bookings
  FOR SELECT
  TO authenticated
  USING ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS bookings_insert_own ON public.bookings;
CREATE POLICY bookings_insert_own
  ON public.bookings
  FOR INSERT
  TO authenticated
  WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS bookings_update_own ON public.bookings;
CREATE POLICY bookings_update_own
  ON public.bookings
  FOR UPDATE
  TO authenticated
  USING ((select auth.uid()) = user_id)
  WITH CHECK ((select auth.uid()) = user_id);

-- accommodations
DROP POLICY IF EXISTS accommodations_mutate_own ON public.accommodations;
CREATE POLICY accommodations_mutate_own
  ON public.accommodations
  FOR ALL
  TO authenticated
  USING (trip_id IN (SELECT id FROM public.trips WHERE user_id = (select auth.uid())))
  WITH CHECK (trip_id IN (SELECT id FROM public.trips WHERE user_id = (select auth.uid())));

-- api gateway config + user settings + api keys
DROP POLICY IF EXISTS api_gateway_configs_owner ON public.api_gateway_configs;
CREATE POLICY api_gateway_configs_owner
  ON public.api_gateway_configs
  FOR ALL
  TO authenticated
  USING ((select auth.uid()) = user_id)
  WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS user_settings_owner ON public.user_settings;
CREATE POLICY user_settings_owner
  ON public.user_settings
  FOR ALL
  TO authenticated
  USING ((select auth.uid()) = user_id)
  WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS api_keys_owner ON public.api_keys;
CREATE POLICY api_keys_owner
  ON public.api_keys
  FOR ALL
  TO authenticated
  USING ((select auth.uid()) = user_id)
  WITH CHECK ((select auth.uid()) = user_id);

-- memories (custom schema)
DROP POLICY IF EXISTS memories_sessions_owner ON memories.sessions;
CREATE POLICY memories_sessions_owner
  ON memories.sessions
  FOR ALL
  TO authenticated
  USING ((select auth.uid()) = user_id)
  WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS memories_turns_owner ON memories.turns;
CREATE POLICY memories_turns_owner
  ON memories.turns
  FOR ALL
  TO authenticated
  USING ((select auth.uid()) = user_id)
  WITH CHECK ((select auth.uid()) = user_id);

CREATE INDEX IF NOT EXISTS idx_memories_turns_user_id
  ON memories.turns (user_id);

DROP POLICY IF EXISTS memories_turn_embeddings_owner ON memories.turn_embeddings;
CREATE POLICY memories_turn_embeddings_owner
  ON memories.turn_embeddings
  FOR ALL
  TO authenticated
  USING (turn_id IN (SELECT id FROM memories.turns WHERE user_id = (select auth.uid())))
  WITH CHECK (turn_id IN (SELECT id FROM memories.turns WHERE user_id = (select auth.uid())));

-- search tables
DROP POLICY IF EXISTS search_destinations_owner ON public.search_destinations;
CREATE POLICY search_destinations_owner
  ON public.search_destinations
  FOR ALL
  TO authenticated
  USING ((select auth.uid()) = user_id)
  WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS search_activities_owner ON public.search_activities;
CREATE POLICY search_activities_owner
  ON public.search_activities
  FOR ALL
  TO authenticated
  USING ((select auth.uid()) = user_id)
  WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS search_flights_owner ON public.search_flights;
CREATE POLICY search_flights_owner
  ON public.search_flights
  FOR ALL
  TO authenticated
  USING ((select auth.uid()) = user_id)
  WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS search_hotels_owner ON public.search_hotels;
CREATE POLICY search_hotels_owner
  ON public.search_hotels
  FOR ALL
  TO authenticated
  USING ((select auth.uid()) = user_id)
  WITH CHECK ((select auth.uid()) = user_id);

-- ===========================
-- STORAGE POLICIES
-- ===========================

DROP POLICY IF EXISTS "Users can upload their own avatar" ON storage.objects;
CREATE POLICY "Users can upload their own avatar"
  ON storage.objects
  FOR INSERT
  TO authenticated
  WITH CHECK (
    bucket_id = 'avatars'
    AND (
      name = (select auth.uid())::text || '.jpg'
      OR name = (select auth.uid())::text || '.png'
      OR name = (select auth.uid())::text || '.gif'
      OR name = (select auth.uid())::text || '.webp'
      OR name = (select auth.uid())::text || '.avif'
    )
  );

DROP POLICY IF EXISTS "Users can update their own avatar" ON storage.objects;
CREATE POLICY "Users can update their own avatar"
  ON storage.objects
  FOR UPDATE
  TO authenticated
  USING (
    bucket_id = 'avatars'
    AND coalesce(owner_id::text, owner::text) = (select auth.uid())::text
  )
  WITH CHECK (
    bucket_id = 'avatars'
    AND coalesce(owner_id::text, owner::text) = (select auth.uid())::text
  );

DROP POLICY IF EXISTS "Users can delete their own avatar" ON storage.objects;
CREATE POLICY "Users can delete their own avatar"
  ON storage.objects
  FOR DELETE
  TO authenticated
  USING (
    bucket_id = 'avatars'
    AND coalesce(owner_id::text, owner::text) = (select auth.uid())::text
  );

DROP POLICY IF EXISTS "Users can upload trip images" ON storage.objects;
CREATE POLICY "Users can upload trip images"
  ON storage.objects
  FOR INSERT
  TO authenticated
  WITH CHECK (
    bucket_id = 'trip-images'
    AND public.user_has_trip_access((select auth.uid()), public.extract_trip_id_from_path(name))
  );

DROP POLICY IF EXISTS "Users can view trip images" ON storage.objects;
CREATE POLICY "Users can view trip images"
  ON storage.objects
  FOR SELECT
  TO authenticated
  USING (
    bucket_id = 'trip-images'
    AND public.user_has_trip_access((select auth.uid()), public.extract_trip_id_from_path(name))
  );

DROP POLICY IF EXISTS "Users can update their trip images" ON storage.objects;
CREATE POLICY "Users can update their trip images"
  ON storage.objects
  FOR UPDATE
  TO authenticated
  USING (
    bucket_id = 'trip-images'
    AND (
      coalesce(owner_id::text, owner::text) = (select auth.uid())::text
      OR public.user_has_trip_edit_access((select auth.uid()), public.extract_trip_id_from_path(name))
    )
  )
  WITH CHECK (
    bucket_id = 'trip-images'
    AND (
      coalesce(owner_id::text, owner::text) = (select auth.uid())::text
      OR public.user_has_trip_edit_access((select auth.uid()), public.extract_trip_id_from_path(name))
    )
  );

DROP POLICY IF EXISTS "Users can delete trip images" ON storage.objects;
CREATE POLICY "Users can delete trip images"
  ON storage.objects
  FOR DELETE
  TO authenticated
  USING (
    bucket_id = 'trip-images'
    AND (
      coalesce(owner_id::text, owner::text) = (select auth.uid())::text
      OR public.user_has_trip_edit_access((select auth.uid()), public.extract_trip_id_from_path(name))
    )
  );

-- ===========================
-- REALTIME (broadcast/presence)
-- ===========================

DO $do$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'realtime'
      AND table_name = 'messages'
  ) THEN
    EXECUTE 'ALTER TABLE realtime.messages ENABLE ROW LEVEL SECURITY';

    EXECUTE 'DROP POLICY IF EXISTS "rtm_trip_topic_read" ON realtime.messages';
    EXECUTE 'DROP POLICY IF EXISTS "rtm_trip_topic_write" ON realtime.messages';
    EXECUTE 'DROP POLICY IF EXISTS "rtm_user_topic_read" ON realtime.messages';
    EXECUTE 'DROP POLICY IF EXISTS "rtm_user_topic_write" ON realtime.messages';

    EXECUTE $pol$
      CREATE POLICY "rtm_trip_topic_read"
      ON realtime.messages
      FOR SELECT
      TO authenticated
      USING (
        realtime.topic() ~ '^trip:[0-9]+$'
        AND public.user_has_trip_access((select auth.uid()), public.try_cast_bigint(public.rt_topic_suffix()))
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
        AND public.user_has_trip_access((select auth.uid()), public.try_cast_bigint(public.rt_topic_suffix()))
        AND realtime.messages.extension IN ('broadcast', 'presence')
      )
    $pol$;

    EXECUTE $pol$
      CREATE POLICY "rtm_user_topic_read"
      ON realtime.messages
      FOR SELECT
      TO authenticated
      USING (
        realtime.topic() ~* '^user:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        AND lower(public.rt_topic_suffix()) = lower((select auth.uid())::text)
        AND realtime.messages.extension IN ('broadcast', 'presence')
      )
    $pol$;

    EXECUTE $pol$
      CREATE POLICY "rtm_user_topic_write"
      ON realtime.messages
      FOR INSERT
      TO authenticated
      WITH CHECK (
        realtime.topic() ~* '^user:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        AND lower(public.rt_topic_suffix()) = lower((select auth.uid())::text)
        AND realtime.messages.extension IN ('broadcast', 'presence')
      )
    $pol$;
  END IF;
END $do$;
