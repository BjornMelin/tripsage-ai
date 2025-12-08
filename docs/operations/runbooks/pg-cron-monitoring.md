# pg_cron Monitoring (Datadog Skeleton)

Purpose: alert when scheduled `pg_cron` jobs (especially memory retention) fail or stop running.

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

## Gaps / next steps

- Wire log shipping from Supabase/Postgres to Datadog (or equivalent) if not already enabled.
- Add a second monitor for execution gaps using Datadog Metrics or synthetic heartbeat if log access is unavailable.
- Keep job name aligned with migration (`cleanup_memories_180d` unless renamed). Update the monitor when retention job names change.
