# Administrator Guide

Admin surfaces are implemented in Next.js route handlers and rely on Supabase SSR sessions. Admin identity is asserted via `app_metadata.is_admin === true` on the Supabase user object (`ensureAdmin` helper).

## Access requirements

- Valid Supabase session cookie (SSR) with `app_metadata.is_admin: true`.
- Environment variables populated for Supabase + Upstash (see `docs/operations/deployment-guide.md`).
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
- Writes emit OpenTelemetry spans (`config.update`) and are rate limited via `withApiGuards`.
- Rollback keeps one canonical history; no parallel config tracks.

### Dashboard metrics

```http
GET /api/dashboard?window=24h|7d|30d|all
```

- Auth required; rate limited as `dashboard:metrics`.
- Returns cached aggregates (Upstash Redis cache-aside) with private cache headers.

## Operational playbook

1) **Verify admin session**

    ```bash
    curl -I -b "sb=<session-cookie>" https://<app>/api/config/agents
    # expect 200 for admins, 403 otherwise
    ```

2) **Update agent config**

    ```bash
    curl -X PUT https://<app>/api/config/agents/budget \
      -b "sb=<session-cookie>" \
      -H "Content-Type: application/json" \
      -d '{"modelId":"gpt-4o-mini","temperature":0.3,"scope":"global"}'
    ```

3) **Rollback**

    ```bash
    curl -X POST https://<app>/api/config/agents/budget/rollback/<versionId> \
      -b "sb=<session-cookie>"
    ```

4) **Metrics sanity check**

    ```bash
    curl -b "sb=<session-cookie>" "https://<app>/api/dashboard?window=24h"
    ```

## Security & auditing

- Admin auth comes solely from Supabase `app_metadata.is_admin`; there are no parallel RBAC tables.
- Secrets and BYOK values remain in Supabase Vault; admin routes never return raw keys.
- All admin routes emit OTEL spans; failures attach `status`, `reason`, and request ID. Scrape via your OTLP/Jaeger pipeline.

## Troubleshooting

- **403 on admin routes**: confirm session cookie present and `app_metadata.is_admin` true in Supabase dashboard.
- **429**: rate limit buckets (`dashboard:metrics`, `config:update`) are powered by Upstash; verify `UPSTASH_*` envs.
- **Config drift**: use `/api/config/agents/:agentType/versions` to confirm latest version; rollback if necessary.
- **Missing telemetry**: ensure OTLP exporter envs (`NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT` for client, server exporter config in code) are set in the environment.
