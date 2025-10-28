-- Update webhook_configs to point to deployed Edge Functions (inactive by default)
-- Safe/idempotent upserts using ON CONFLICT(name)

DO $$
BEGIN
  -- Trip notifications
  INSERT INTO public.webhook_configs(name, url, events, headers, is_active)
  VALUES (
    'trip_notifications',
    'https://<PROJECT_REF>.supabase.co/functions/v1/trip-notifications',
    ARRAY['trip.reminder','collaborator.invited','booking.confirmed'],
    '{}'::jsonb,
    false
  )
  ON CONFLICT (name) DO UPDATE
  SET url = EXCLUDED.url,
      events = EXCLUDED.events,
      headers = EXCLUDED.headers;

  -- File processing
  INSERT INTO public.webhook_configs(name, url, events, headers, is_active)
  VALUES (
    'file_processing',
    'https://<PROJECT_REF>.supabase.co/functions/v1/file-processing',
    ARRAY['storage.file.uploaded','storage.file.updated'],
    '{}'::jsonb,
    false
  )
  ON CONFLICT (name) DO UPDATE
  SET url = EXCLUDED.url,
      events = EXCLUDED.events,
      headers = EXCLUDED.headers;

  -- Cache invalidation
  INSERT INTO public.webhook_configs(name, url, events, headers, is_active)
  VALUES (
    'cache_invalidation',
    'https://<PROJECT_REF>.supabase.co/functions/v1/cache-invalidation',
    ARRAY['content.published','content.updated','content.deleted'],
    '{}'::jsonb,
    false
  )
  ON CONFLICT (name) DO UPDATE
  SET url = EXCLUDED.url,
      events = EXCLUDED.events,
      headers = EXCLUDED.headers;
END$$;
