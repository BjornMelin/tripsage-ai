-- Realtime helper functions and index improvements
-- Date: 2025-10-27
-- Purpose: Factor reusable helpers for Realtime Authorization policies and add supporting indexes

-- Helper to get current Realtime topic prefix (user/session)
create or replace function public.rt_topic_prefix()
returns text
language sql
stable
as $$ select split_part(realtime.topic(), ':', 1) $$;

-- Helper to get current Realtime topic suffix (id component)
create or replace function public.rt_topic_suffix()
returns text
language sql
stable
as $$ select split_part(realtime.topic(), ':', 2) $$;

-- Helper to check if current user is a member of session's trip (owner or collaborator)
create or replace function public.rt_is_session_member()
returns boolean
language plpgsql
stable
as $$
declare ok boolean := false;
begin
  if to_regclass('public.chat_sessions') is null then
    return false;
  end if;
  execute 'select exists (
    select 1
    from public.chat_sessions cs
    left join public.trips t on t.id = cs.trip_id
    left join public.trip_collaborators tc on tc.trip_id = cs.trip_id and tc.user_id = auth.uid()
    where cs.id = (public.rt_topic_suffix())::uuid
      and (
        cs.user_id = auth.uid()
        or t.user_id = auth.uid()
        or tc.user_id is not null
      )
  )' into ok;
  return ok;
end;
$$;

-- Supporting indexes (no-ops if already present)
DO $do$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='chat_sessions') THEN
    EXECUTE 'create index if not exists idx_chat_sessions_id on public.chat_sessions (id)';
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='trips') THEN
    EXECUTE 'create index if not exists idx_trips_id_user on public.trips (id, user_id)';
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='trip_collaborators') THEN
    EXECUTE 'create index if not exists idx_trip_collaborators_trip_user on public.trip_collaborators (trip_id, user_id)';
  END IF;
END $do$;

-- Recreate concise policies using helpers
drop policy if exists "rtm_user_topic_read" on "realtime"."messages";
drop policy if exists "rtm_user_topic_write" on "realtime"."messages";
drop policy if exists "rtm_session_topic_read" on "realtime"."messages";
drop policy if exists "rtm_session_topic_write" on "realtime"."messages";

-- user:{sub}
create policy "rtm_user_topic_read"
on "realtime"."messages"
for select
to authenticated
using (
  public.rt_topic_prefix() = 'user'
  and public.rt_topic_suffix() = auth.uid()::text
  and "realtime"."messages"."extension" in ('broadcast','presence')
);

create policy "rtm_user_topic_write"
on "realtime"."messages"
for insert
to authenticated
with check (
  public.rt_topic_prefix() = 'user'
  and public.rt_topic_suffix() = auth.uid()::text
  and "realtime"."messages"."extension" in ('broadcast','presence')
);

-- session:{uuid}
DO $do$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='chat_sessions') THEN
    EXECUTE $$create policy "rtm_session_topic_read" on "realtime"."messages" for select to authenticated using (
      public.rt_topic_prefix() = 'session'
      and public.rt_is_session_member()
      and "realtime"."messages"."extension" in ('broadcast','presence')
    )$$;
    EXECUTE $$create policy "rtm_session_topic_write" on "realtime"."messages" for insert to authenticated with check (
      public.rt_topic_prefix() = 'session'
      and public.rt_is_session_member()
      and "realtime"."messages"."extension" in ('broadcast','presence')
    )$$;
  END IF;
END $do$;

do $$ begin
  raise notice '✅ Realtime helpers and policies updated';
end $$;
