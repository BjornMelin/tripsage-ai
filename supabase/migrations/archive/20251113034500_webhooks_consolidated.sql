-- Consolidated webhook migrations (FINAL)
-- Enables pg_net/pgcrypto and installs HTTP webhook triggers to Vercel
-- for trips (collaborators) and cache-relevant tables. Includes HMAC header
-- and pinned search_path for SECURITY DEFINER functions.

-- Enable required extensions
create extension if not exists pg_net;
create extension if not exists pgcrypto;

-- Optional cleanup of legacy function (if present)
DO $$
BEGIN
  BEGIN
    EXECUTE 'DROP FUNCTION IF EXISTS send_edge_function_webhook(text, jsonb)';
  EXCEPTION WHEN undefined_function THEN
    -- ignore
  END;
END $$;

-- Trip collaborators → Vercel webhook (HMAC-signed)
create or replace function public.notify_trip_collaborators_http() returns trigger as $$
declare
  url text := current_setting('app.vercel_webhook_trips', true);
  secret text := current_setting('app.webhook_hmac_secret', true);
  payload jsonb;
  signature text;
begin
  if url is null then
    return coalesce(new, old);
  end if;

  payload := jsonb_build_object(
    'type', tg_op,
    'table', tg_table_name,
    'schema', tg_table_schema,
    'record', case when tg_op = 'DELETE' then to_jsonb(old) else to_jsonb(new) end,
    'old_record', case when tg_op = 'UPDATE' then to_jsonb(old) else null end,
    'occurred_at', now()
  );

  if secret is not null then
    signature := encode(hmac(convert_to(payload::text, 'utf8'), convert_to(secret, 'utf8'), 'sha256'), 'hex');
  end if;

  perform supabase_functions.http_request(
    url,
    'POST',
    jsonb_strip_nulls(jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Event-Type', tg_op,
      'X-Table', tg_table_name,
      'X-Signature-HMAC', signature
    )),
    payload,
    8000
  );

  return coalesce(new, old);
end;
$$ language plpgsql security definer set search_path = pg_catalog, public;

drop trigger if exists trg_trip_collaborators_webhook_http on public.trip_collaborators;
create trigger trg_trip_collaborators_webhook_http
after insert or update or delete on public.trip_collaborators
for each row execute function public.notify_trip_collaborators_http();

-- Generic cache invalidation webhook (versioned tag bump in app)
create or replace function public.notify_table_change_cache_http() returns trigger as $$
declare
  url text := current_setting('app.vercel_webhook_cache', true);
  secret text := current_setting('app.webhook_hmac_secret', true);
  payload jsonb;
  signature text;
begin
  if url is null then
    return coalesce(new, old);
  end if;

  payload := jsonb_build_object(
    'type', tg_op,
    'table', tg_table_name,
    'schema', tg_table_schema,
    'record', case when tg_op = 'DELETE' then to_jsonb(old) else to_jsonb(new) end,
    'old_record', case when tg_op = 'UPDATE' then to_jsonb(old) else null end,
    'occurred_at', now()
  );

  if secret is not null then
    signature := encode(hmac(convert_to(payload::text, 'utf8'), convert_to(secret, 'utf8'), 'sha256'), 'hex');
  end if;

  perform supabase_functions.http_request(
    url,
    'POST',
    jsonb_strip_nulls(jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Event-Type', tg_op,
      'X-Table', tg_table_name,
      'X-Signature-HMAC', signature
    )),
    payload,
    8000
  );

  return coalesce(new, old);
end;
$$ language plpgsql security definer set search_path = pg_catalog, public;

-- Triggers for cache-relevant tables
drop trigger if exists trg_trips_cache_webhook on public.trips;
create trigger trg_trips_cache_webhook after insert or update or delete on public.trips
for each row execute function public.notify_table_change_cache_http();

drop trigger if exists trg_flights_cache_webhook on public.flights;
create trigger trg_flights_cache_webhook after insert or update or delete on public.flights
for each row execute function public.notify_table_change_cache_http();

drop trigger if exists trg_accommodations_cache_webhook on public.accommodations;
create trigger trg_accommodations_cache_webhook after insert or update or delete on public.accommodations
for each row execute function public.notify_table_change_cache_http();

drop trigger if exists trg_search_destinations_cache_webhook on public.search_destinations;
create trigger trg_search_destinations_cache_webhook after insert or update or delete on public.search_destinations
for each row execute function public.notify_table_change_cache_http();

drop trigger if exists trg_search_flights_cache_webhook on public.search_flights;
create trigger trg_search_flights_cache_webhook after insert or update or delete on public.search_flights
for each row execute function public.notify_table_change_cache_http();

drop trigger if exists trg_search_hotels_cache_webhook on public.search_hotels;
create trigger trg_search_hotels_cache_webhook after insert or update or delete on public.search_hotels
for each row execute function public.notify_table_change_cache_http();

drop trigger if exists trg_search_activities_cache_webhook on public.search_activities;
create trigger trg_search_activities_cache_webhook after insert or update or delete on public.search_activities
for each row execute function public.notify_table_change_cache_http();

drop trigger if exists trg_chat_messages_cache_webhook on public.chat_messages;
create trigger trg_chat_messages_cache_webhook after insert or update or delete on public.chat_messages
for each row execute function public.notify_table_change_cache_http();

drop trigger if exists trg_chat_sessions_cache_webhook on public.chat_sessions;
create trigger trg_chat_sessions_cache_webhook after insert or update or delete on public.chat_sessions
for each row execute function public.notify_table_change_cache_http();

