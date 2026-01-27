# Administrator Guide

Admin surfaces are implemented in Next.js route handlers and rely on Supabase SSR sessions. Admin identity is asserted via `app_metadata.is_admin === true` on the Supabase user object (`ensureAdmin` helper).

## Access requirements

- Valid Supabase session cookie (SSR) with `app_metadata.is_admin: true`.
- Environment variables populated for Supabase + Upstash (see [Deployment Guide](deployment-guide.md#required-environment-variables)).
- Admin routes are telemetry-instrumented; no server `console.*`.

## Admin endpoints

### Agent configuration (versioned)

All endpoints enforce `ensureAdmin(user)` and run on the Node runtime.

```http
GET  /api/config/agents                 # list agent types + scopes
GET  /api/config/agents/:agentType      # fetch active config (supports ?scope=global|env)
PUT  /api/config/agents/:agentType      # update config (Zod-validated)
GET  /api/config/agents/:agentType/versions
POST /api/config/agents/:agentType/rollback/:versionId
```

- Scope parsing uses `scopeSchema` (`global` default).
- Writes emit OpenTelemetry spans (`agent_config.load_existing`, `agent_config.update_failed`, `agent_config.updated`) and are rate limited via `withApiGuards`.
- Rollback keeps one canonical history; no parallel config tracks.

### Dashboard metrics

```http
GET /api/dashboard?window=24h|7d|30d|all
```

- Auth required; rate limited as `dashboard:metrics`.
- Returns cached aggregates (Upstash Redis cache-aside) with private cache headers.

## Operational playbook

> **Supabase SSR Cookies**: Authenticated requests require two session cookies from the Supabase SSR setup: `sb-access-token` (access token) and `sb-refresh-token` (refresh token). Pass both via `-b` flags in curl requests.

1) **Verify admin session**

    ```bash
    curl -I \
      -b "sb-access-token=<access-token>" \
      -b "sb-refresh-token=<refresh-token>" \
      https://<app>/api/config/agents
    # expect 200 for admins, 403 otherwise
    ```

2) **Update agent config**

    ```bash
    curl -X PUT https://<app>/api/config/agents/budget \
      -b "sb-access-token=<access-token>" \
      -b "sb-refresh-token=<refresh-token>" \
      -H "Content-Type: application/json" \
      -d '{"modelId":"gpt-4o-mini","temperature":0.3,"scope":"global"}'
    ```

3) **Rollback**

    ```bash
    curl -X POST https://<app>/api/config/agents/budget/rollback/<versionId> \
      -b "sb-access-token=<access-token>" \
      -b "sb-refresh-token=<refresh-token>"
    ```

4) **Metrics sanity check**

    ```bash
    curl -b "sb-access-token=<access-token>" \
      -b "sb-refresh-token=<refresh-token>" \
      "https://<app>/api/dashboard?window=24h"
    ```

## Data migrations

### Agent config normalization (id format)

Do you need to run this migration?

- **No** if your base schema migration ran on or after **2026-01-24**.
- **Yes** if the base schema ran before **2026-01-24** or you manage migrations
  manually. Run the pre-checks below; if both counts are 0, skip the migration.

Prerequisite: `gen_random_uuid()` requires the Postgres `pgcrypto` extension.
Supabase enables `pgcrypto` by default; self-managed Postgres must enable it
before running the `UPDATE`s on `agent_config` and `agent_config_versions`.
Run:

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

Tip: creating extensions typically requires superuser or database owner
permissions (or a role granted `CREATE` on the database).

```sql
-- Pre-migration checks (skip if both counts are 0)
SELECT COUNT(*) AS agent_config_invalid
FROM agent_config
WHERE (config->>'id') IS NULL OR NOT (config->>'id') ~ '^v\\d+_[a-f0-9]{8}$';

SELECT COUNT(*) AS agent_config_versions_invalid
FROM agent_config_versions
WHERE (config->>'id') IS NULL OR NOT (config->>'id') ~ '^v\\d+_[a-f0-9]{8}$';

BEGIN;

UPDATE agent_config
SET config = jsonb_set(
  config,
  '{id}',
  to_jsonb(
    concat(
      'v',
      extract(epoch from COALESCE(created_at, clock_timestamp()))::bigint,
      '_',
      substr(md5(COALESCE(version_id::text, gen_random_uuid()::text)), 1, 8)
    )
  ),
  true
)
WHERE (config->>'id') IS NULL OR NOT (config->>'id') ~ '^v\\d+_[a-f0-9]{8}$';

UPDATE agent_config_versions
SET config = jsonb_set(
  config,
  '{id}',
  to_jsonb(
    concat(
      'v',
      extract(epoch from COALESCE(created_at, clock_timestamp()))::bigint,
      '_',
      substr(md5(COALESCE(id::text, gen_random_uuid()::text)), 1, 8)
    )
  ),
  true
)
WHERE (config->>'id') IS NULL OR NOT (config->>'id') ~ '^v\\d+_[a-f0-9]{8}$';

-- Post-migration checks (expect both counts to be 0)
SELECT COUNT(*) AS agent_config_invalid
FROM agent_config
WHERE (config->>'id') IS NULL OR NOT (config->>'id') ~ '^v\\d+_[a-f0-9]{8}$';

SELECT COUNT(*) AS agent_config_versions_invalid
FROM agent_config_versions
WHERE (config->>'id') IS NULL OR NOT (config->>'id') ~ '^v\\d+_[a-f0-9]{8}$';

COMMIT;
```

If any statement errors, the transaction rolls back. Inspect the error output,
fix any schema or data issues (missing extension, invalid columns, permissions),
and retry the migration.

## Security & auditing

- Admin auth comes solely from Supabase `app_metadata.is_admin`; there are no parallel RBAC tables.
- Secrets and BYOK values remain in Supabase Vault; admin routes never return raw keys.
- All admin routes emit OTEL spans; failures attach `status`, `reason`, and request ID. Scrape via your OTLP/Jaeger pipeline.

## Troubleshooting

- **403 on admin routes**: confirm session cookie present and `app_metadata.is_admin` true in Supabase dashboard.
- **429**: rate limit buckets (`dashboard:metrics`, `config:agents:read`, `config:agents:update`, `config:agents:rollback`, `config:agents:versions`) are powered by Upstash; verify `UPSTASH_*` envs.
- **Config drift**: use `/api/config/agents/:agentType/versions` to confirm latest version; rollback if necessary.
- **Missing telemetry**: ensure OTLP exporter envs (`NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT` for client, server exporter config in code) are set in the environment.
