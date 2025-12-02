-- Scheduled cleanup for expired MFA enrollments
-- Removes expired or consumed enrollments older than 1 day to keep table small.

-- Requires pg_cron extension (enabled by default on Supabase).
select cron.schedule(
  'mfa_enrollments_cleanup_daily',
  '0 3 * * *',
  $$DELETE FROM public.mfa_enrollments
    WHERE status IN ('expired','consumed')
      AND expires_at < timezone('utc'::text, now()) - interval '1 day';$$
);

comment on cron.job is 'Daily cleanup of expired/consumed MFA enrollments';
