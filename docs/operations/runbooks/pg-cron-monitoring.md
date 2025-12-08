# pg_cron Monitoring (Datadog Skeleton)

Purpose: alert when scheduled `pg_cron` jobs (especially memory retention) fail or stop running. Job name `cleanup_memories_180d` comes from `supabase/migrations/20251122000000_base_schema.sql`; if the migration renames the job, update this runbook and the monitors below.

## What to monitor

- Job failures in Postgres logs containing `pg_cron` + job name (default: `cleanup_memories_180d`).
- Missing executions for >2 intervals (default cron: `45 3 * * *`).

## Datadog monitor template

```json
{
  "name": "[TripSage] pg_cron cleanup_memories_180d failures",
  "type": "log alert",
  "query": "service:postgres @message:\"pg_cron\" @message:\"cleanup_memories_180d\" @status:error",
  "message": "pg_cron cleanup_memories_180d is failing. Investigate Supabase logs and rerun the job. See docs/operations/runbooks/pg-cron-monitoring.md",
  "tags": ["service:postgres", "component:pg_cron", "env:prod"],
  "options": {
    "evaluation_delay": 300,
    "no_data_timeframe": 1440,
    "notify_no_data": true,
    "thresholds": { "critical": 1 }
  }
}
```

## Remediation

1) **Confirm job status**
   - Supabase UI → Database → Extensions → `pg_cron` → Job History, or query `SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 20;`.
   - Check expected job exists: `SELECT jobid, schedule, command FROM cron.job WHERE command LIKE '%cleanup_memories_180d%';`.

2) **Inspect recent runs and errors**
   - Recent run outcomes: `SELECT * FROM cron.job_run_details WHERE jobid = (SELECT jobid FROM cron.job WHERE command LIKE '%cleanup_memories_180d%' LIMIT 1) ORDER BY start_time DESC LIMIT 50;`.
   - Postgres logs (via Datadog or Supabase logs) filtered on `pg_cron` + job name; capture error snippets for escalation.

3) **Check locks / long transactions before rerun**
   - Blocking locks: `SELECT * FROM pg_locks pl JOIN pg_stat_activity psa ON pl.pid = psa.pid WHERE psa.query ILIKE '%cleanup_memories_180d%';`.
   - Long-running statements: `SELECT pid, now() - query_start AS age, query FROM pg_stat_activity WHERE state != 'idle' ORDER BY age DESC LIMIT 20;`.

4) **Verify idempotency and safe rerun options**
   - `cleanup_memories_180d` deletes expired rows; reruns should be no-op after successful completion. Confirm by reviewing migration notes and WHERE clause window.
   - For safety, dry-run on staging first (Supabase staging project) using same command and parameters.

5) **Run job manually (single execution)**
   - From Supabase SQL editor or psql: `SELECT cron.schedule_in_database('cleanup_memories_180d_manual', 'now()', $$SELECT cleanup_memories_180d();$$);` then monitor `cron.job_run_details` for that job name; drop the temp job after success: `SELECT cron.unschedule('cleanup_memories_180d_manual');`.

6) **Escalate if**
   - Two consecutive manual runs fail, or production data at risk (unexpected deletions/retention anomalies), or locks persist >15 minutes.
   - Provide: job_run_details rows, log snippets (last error stack), lock query output, and whether staging rerun succeeded.
   - Temporary mitigation: pause schedule `SELECT cron.unschedule('cleanup_memories_180d');` **only after explicit approval** (record approver name/title, channel, timestamp in the incident ticket or #ops-alerts thread). Unscheduling is effectively irreversible without manual reschedule/rerun; document the pause, planned reschedule time, and owner.

## Gaps / next steps (actionable)

- **Jira Epic OPS-2450 — pg_cron monitoring hardening** (Owner: Platform Team, Target: 2026-01-15)
  - OPS-2451 (Owner: Platform Team, Priority: P0/Blocker, Due: 2025-12-15): Enable Supabase/Postgres → Datadog log shipping and confirm `pg_cron` entries land in `service:postgres` logs.
  - OPS-2452 (Owner: SRE, Priority: P1, Due: 2025-12-18): Deploy the log alert in this doc using the enabled log pipeline; validate alert fires on a forced failure.
  - OPS-2453 (Owner: SRE, Priority: P1, Due: 2025-12-22, dependent on OPS-2451): Add execution-gap monitor via Datadog metrics; if OPS-2451 slips, implement the heartbeat/synthetic metric workaround as the interim monitoring path and note the dependency/owner in the issue.
  - OPS-2454 (Owner: Product/Platform, Priority: P2, Due: 2026-01-05): Keep job name aligned with migrations (`cleanup_memories_180d` unless renamed); add a migration checklist step to update alert queries when job names change.
  - OPS-2455 (Owner: Platform Team, Priority: P2, Due: 2026-01-05): Document and automate rollout playbook (enable log shipping + monitors) for new environments; link playbook in this runbook.
