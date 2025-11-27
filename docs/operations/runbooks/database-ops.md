# Database Operations Runbook

Task-focused guide for Supabase operations. For schema/design context, see `../../architecture/database.md`.

## Scope & Prerequisites

- Supabase CLI installed and authenticated (`supabase --version`, `supabase login`).
- Access to project `project-ref`, service role key, and Vault-enabled Supabase project.
- Local env ready for this repo (PNPM, Node, `supabase` directory present).

## Bootstrap a Database

### Local Dev Stack

1. Start services: `supabase start`
2. Reset and apply migrations: `supabase db reset`
3. (Alt) Apply canonical schema to external Postgres: `cd supabase && psql "$DATABASE_URL" -f schema.sql`

### New Supabase Project

1. Create project in dashboard; capture `project-ref` and DB URL.
2. Link repo: `supabase link --project-ref <project-ref>`
3. Push schema + seed: `supabase db push --include-seed`
4. Generate types after changes: `supabase gen types typescript --local > frontend/src/lib/supabase/database.types.ts`

### Required Environment Variables

- `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY` (server only)
- `AI_GATEWAY_API_KEY`, `AI_GATEWAY_URL` (team fallback)
- Optional user-provided BYOK keys via Vault
- Server-side fallback provider keys (optional): `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `XAI_API_KEY`
- Webhooks/QStash/Resend: `HMAC_SECRET`, `QSTASH_TOKEN`, `QSTASH_CURRENT_SIGNING_KEY`, `QSTASH_NEXT_SIGNING_KEY`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `RESEND_FROM_NAME`
- Optional downstream collaborator webhook: `COLLAB_WEBHOOK_URL`
- Upstash Redis: `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`

## BYOK / Vault Operations

### Architecture Overview

The BYOK system consists of:

- **Factory Pattern**: `@supabase/ssr` integration with OpenTelemetry tracing
- **Multi-Provider Support**: OpenAI, Anthropic, xAI, OpenRouter, Vercel AI Gateway (5 providers)
- **Vault Storage**: Encrypted API key storage with service-role access only
- **RPC Security**: All operations via 8 SECURITY DEFINER functions
- **RLS Isolation**: Owner-only data access policies
- **SSR Compatibility**: Next.js App Router with proper cookie handling

### One-Time Verification

- Ensure Vault extension is installed:

  ```bash
  supabase db sql "SELECT name, installed_version FROM pg_available_extensions WHERE name = 'vault';"
  ```

- Smoke-test SECURITY DEFINER RPCs (service role): `insert_user_api_key`, `get_user_api_key`, `delete_user_api_key`, `touch_user_api_key` via REST or psql; anon-key should fail.
- Validate gateway helpers: `upsert_user_gateway_config`, `get_user_gateway_base_url`, `get_user_allow_gateway_fallback` (service role only).

### BYOK Lifecycle (service role)

1. Insert key: `insert_user_api_key(user_id, service, key)`
2. Retrieve key: `get_user_api_key(user_id, service)`
3. Touch access time: `touch_user_api_key(user_id, service)`
4. Delete key: `delete_user_api_key(user_id, service)`

Expect RLS isolation: users only see their own keys via app paths.

### BYOK Verification (curl)

```bash
# Negative: anon should fail
curl -X POST https://<project>.supabase.co/rest/v1/rpc/insert_user_api_key \
  -H "Authorization: Bearer <anon-key>" \
  -H "Content-Type: application/json" \
  -d '{"p_user_id":"test","p_service":"openai","p_api_key":"deny"}'

# Positive: service role
curl -X POST https://<project>.supabase.co/rest/v1/rpc/insert_user_api_key \
  -H "Authorization: Bearer '$SUPABASE_SERVICE_ROLE_KEY'" \
  -H "Content-Type: application/json" \
  -d '{"p_user_id":"test","p_service":"openai","p_api_key":"sk-test"}'

# Gateway config
curl -X POST https://<project>.supabase.co/rest/v1/rpc/upsert_user_gateway_config \
  -H "Authorization: Bearer '$SUPABASE_SERVICE_ROLE_KEY'" \
  -H "Content-Type: application/json" \
  -d '{"p_user_id":"test","p_base_url":"https://my-gateway.vercel.sh/v1"}'
```

### Complete BYOK Lifecycle Test

```bash
# 1. Insert API key
curl -X POST https://<project>.supabase.co/rest/v1/rpc/insert_user_api_key \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_user_id": "test-user", "p_service": "openai", "p_api_key": "sk-test-key"}'

# 2. Retrieve API key
curl -X POST https://<project>.supabase.co/rest/v1/rpc/get_user_api_key \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_user_id": "test-user", "p_service": "openai"}'

# 3. Update last_used timestamp
curl -X POST https://<project>.supabase.co/rest/v1/rpc/touch_user_api_key \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_user_id": "test-user", "p_service": "openai"}'

# 4. Delete API key
curl -X POST https://<project>.supabase.co/rest/v1/rpc/delete_user_api_key \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_user_id": "test-user", "p_service": "openai"}'
```

### Integration Testing

**End-to-End BYOK Flow (TypeScript)**:

```ts
import { resolveProvider } from "@ai/models/registry";

// Should use BYOK key if available
const provider = await resolveProvider(userId, "gpt-4o-mini");
expect(provider.provider).toBe("openai");
expect(provider.modelId).toBe("gpt-4o-mini");

// Should fallback to team Gateway (remove BYOK keys first)
const fallbackProvider = await resolveProvider(userId, "gpt-4o-mini");
expect(fallbackProvider.provider).toBe("openai");
```

**SSR Compatibility Testing**:

```ts
import { createServerSupabase } from "@/lib/supabase/server";
import { getCurrentUser } from "@/lib/supabase/factory";

const supabase = await createServerSupabase();
const user = await getCurrentUser(supabase);
expect(user).toBeDefined();
```

## Webhooks Operations (DB → Vercel)

### Prerequisites

- Webhook routes deployed: `/api/hooks/trips`, `/api/hooks/cache`, `/api/hooks/files`, `/api/jobs/notify-collaborators` (QStash worker)
- Env vars configured: `HMAC_SECRET`, `QSTASH_*`, `RESEND_*` (see Required Environment Variables above)
- QStash worker rejects requests when signing keys are missing; configure before directing production traffic

### Configure Postgres GUCs

Set once per database (replace values):

```sql
ALTER DATABASE <db_name>
  SET app.vercel_webhook_trips = 'https://<vercel-domain>/api/hooks/trips';
ALTER DATABASE <db_name>
  SET app.vercel_webhook_cache = 'https://<vercel-domain>/api/hooks/cache';
ALTER DATABASE <db_name>
  SET app.webhook_hmac_secret   = '<same-as-HMAC_SECRET>';

-- Verify
SELECT current_setting('app.vercel_webhook_trips', true) AS trips_url,
       current_setting('app.vercel_webhook_cache', true) AS cache_url,
       nullif(current_setting('app.webhook_hmac_secret', true), '') IS NOT NULL AS hmac_set;
```

Notes:

- Use `SET` per-session for testing; functions use `current_setting(..., true)` which returns NULL when unset
- **Secret rotation**: update DB GUC and Vercel env atomically; briefly accept both during rotation if needed
- Automate with `scripts/operators/setup_webhooks.sh`; validate with `scripts/operators/verify_webhook_secret.sh`
- `.github/workflows/deploy.yml` runs the verification script before deployment; configure `PRIMARY_DATABASE_URL` secret

### Test HMAC Delivery

```bash
payload='{"type":"INSERT","table":"trip_collaborators","record":{"id":"test","trip_id":1},"occurred_at":"2025-11-13T03:00:00Z"}'
sig=$(printf "%s" "$payload" | openssl dgst -sha256 -hmac "$HMAC_SECRET" -hex | sed 's/^.* //')
curl -i -H 'Content-Type: application/json' -H "X-Signature-HMAC: $sig" -d "$payload" https://<vercel-domain>/api/hooks/trips
```

Expected: `200 OK { ok: true }`; `401` on bad/missing signature.

Automate drift detection with `scripts/operators/verify_webhook_secret.sh`; it fails the pipeline when DB GUCs diverge from `HMAC_SECRET`.

### End-to-End from Postgres

- After GUCs are set, mutate a subscribed table (e.g., `INSERT INTO trip_collaborators ...`); trigger posts to Vercel handlers with HMAC
- `/api/hooks/trips` enqueues jobs to `/api/jobs/notify-collaborators` via QStash for durable retries
- `/api/hooks/cache` bumps per-tag version counters in Upstash Redis; downstream cache keys use format `tag:v{version}:{key}` (no Redis purging or downstream webhooks)
- QStash workers validate `Upstash-Signature` header; fail closed when signing keys absent

### Security Notes

- HMAC header omitted when no secret configured; handlers reject missing/invalid signatures
- Webhook functions run with `SECURITY DEFINER` and `search_path = pg_catalog, public` to prevent hijacking
- Keep secrets in DB settings (`app.*` GUCs); never store in tables
- QStash uses `Upstash-Signature` for worker calls; worker routes verify with configured signing keys

### Troubleshooting

- 401 responses: verify `app.webhook_hmac_secret` matches `HMAC_SECRET` exactly (no quotes/whitespace)
- Missing signatures: HMAC header omitted if secret unset; set DB GUC and redeploy env
- QStash failures: ensure `QSTASH_*` envs present; worker rejects missing keys
- Re-compute signature locally using exact JSON the DB sends (`payload::text`) if 401s persist

### Observability

- Webhook handlers emit spans: `webhook.trips`, `webhook.cache`, `webhook.files`
- Verification failures add event `webhook_verification_failed` on active span with reason: `missing_secret_env` | `invalid_signature` | `invalid_json` | `invalid_payload_shape`
- Handlers log structured `[operational-alert]` entries when verification fails; wire log drains or SIEM queries to page on repeated failures
- Redis helpers emit `redis.unavailable` spans and `[operational-alert]` logs when cache invalidation or idempotency degrades due to missing Upstash credentials

## Webhook Types

| Webhook | Trigger Tables | Route | Purpose |
|---------|---------------|-------|---------|
| Trips | `trip_collaborators` | `/api/hooks/trips` | Enqueue collaborator notifications via QStash |
| Cache | `trips`, `flights`, `accommodations`, `search_*`, `chat_*` | `/api/hooks/cache` | Bump cache tag versions in Upstash Redis |
| Files | `file_attachments` | `/api/hooks/files` | Process file uploads |
| Notify (QStash worker) | — | `/api/jobs/notify-collaborators` | Send email notifications via Resend |

## Realtime Operations

| Topic Pattern | Access | Use Case |
|--------------|--------|----------|
| `user:{user_id}` | Subject user only | Per-user notifications, agent status |
| `session:{session_id}` | Session owner + trip collaborators | Chat session updates, typing indicators |
| `trip:{trip_id}` | Trip owner + collaborators | Trip collaboration events |

All channels are private by default (`{ config: { private: true } }`). RLS policies enforce topic ownership via `realtime` extension helpers.

**Client pattern**: Sync access token before subscribing; unsubscribe on unmount to avoid leaks.

## Database Maintenance

### Database Health Check

```sql
-- Active connections with warning threshold
SELECT
  'active_connections' AS metric,
  count(*)::text AS value,
  CASE WHEN count(*) > 150 THEN 'warning' ELSE 'ok' END AS status
FROM pg_stat_activity WHERE state = 'active';
```

### Query Performance

```sql
SELECT query, total_time, calls, total_time/calls AS avg_ms
FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;
```

### Connection Health

```sql
SELECT state, count(*) FROM pg_stat_activity GROUP BY state;
```

### Vector Index Maintenance

```sql
-- Check index stats (accommodation_embeddings uses ivfflat)
SELECT indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes WHERE indexname LIKE '%embedding%';

-- Rebuild when scans climb or recall drops
REINDEX INDEX CONCURRENTLY idx_memories_embedding;

-- Adjust HNSW parameters based on data size (if using HNSW)
ALTER INDEX idx_memories_embedding SET (m = 32, ef_construction = 400);
```

### Backup & Recovery

- Supabase managed daily backups + PITR; verify retention
- Manual exports:

```bash
supabase db dump --db-url "$DATABASE_URL" > backup.sql
pg_dump --table=memories --table=session_memories "$DATABASE_URL" > memories_backup.sql
```

### Schema Migration Naming

```text
YYYYMMDD_HHMMSS_description.sql
# Example: 20251113_143000_add_trip_collaborators.sql
```

Keep table and function inventory aligned with `docs/architecture/database.md`.

## Common Issues & Resolutions

- **Vault extension not accessible**:

```bash
# Check Vault extension status
supabase db sql "SELECT name, installed_version FROM pg_available_extensions WHERE name = 'vault';"

# Re-enable if needed
supabase db sql "CREATE EXTENSION IF NOT EXISTS vault;"
```

- **Must be called as service role**: ensure Authorization header uses service role JWT when invoking RPCs directly; verify JWT claims include `role: "service_role"`

- **RLS policy violation**:

```sql
-- Check RLS policies are active
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('api_keys', 'api_gateway_configs', 'user_settings');
```

- **Provider resolution failed**:
  - Check API key validity for the provider
  - Verify provider is supported (openai, anthropic, xai, openrouter, gateway)
  - Check Gateway fallback settings if no BYOK keys
  - Review telemetry spans `providers.resolve` for path and error details

- **Realtime auth errors**: verify JWT freshness and topic formatting; ensure `realtime` extension present

- **Webhook issues**: see [Webhooks Troubleshooting](#troubleshooting) section above

## Pre-Deployment Checklist

- [ ] Vault extension enabled; BYOK RPCs pass curl smoke tests
- [ ] All 8 SECURITY DEFINER functions operational (4 BYOK + 4 Gateway config)
- [ ] All 5 providers functional (OpenAI, Anthropic, xAI, OpenRouter, Gateway)
- [ ] Webhook GUCs match `HMAC_SECRET`; verification script passes
- [ ] Required env vars present (Supabase, Redis/QStash, HMAC, Resend, AI keys)
- [ ] Migrations applied (consolidated: `20251122000000_base_schema.sql`); types regenerated
- [ ] RLS policies active on: `api_keys`, `api_gateway_configs`, `user_settings`
- [ ] Vector indexes healthy; no critical slow queries in `pg_stat_statements`

### RLS Data Isolation Verification

```sql
-- As service role, insert test data
SELECT insert_user_api_key('user-a'::uuid, 'openai', 'key-a');
SELECT insert_user_api_key('user-b'::uuid, 'openai', 'key-b');

-- Verify isolation (each user should only see their own keys)
-- Test via application RLS policies with user-a JWT
```

## Security Considerations

### Defense in Depth

1. **Network Level**: Supabase project access controls
2. **Application Level**: Service role key authentication
3. **Database Level**: RLS policies and SECURITY DEFINER functions
4. **Encryption Level**: Vault-stored secrets with Supabase encryption
5. **Operational Level**: Audit logging and monitoring

### Compliance Requirements

- **Data Encryption**: All API keys encrypted at rest via Vault
- **Access Logging**: All operations logged with user context
- **Principle of Least Privilege**: Service role only for administrative operations
- **Data Isolation**: RLS ensures users only access their own keys
- **Regular Audits**: Automated verification scripts for continuous compliance

## Monitoring & Alerting

### Telemetry Integration

The BYOK system integrates with OpenTelemetry:

- **Factory Initialization**: `supabase.init` spans with database connection tracking
- **Provider Resolution**: `providers.resolve` spans with user ID redaction and path tracking
- **Auth Operations**: `supabase.auth.getUser` spans for session management
- **Middleware**: Session refresh spans in Edge runtime

### Key Metrics

- BYOK resolution success rate: `sum(rate(providers_resolve_total{status="success"}[5m])) / sum(rate(providers_resolve_total[5m]))`
- Vault operation latency: `histogram_quantile(0.95, rate(vault_operation_duration_bucket[5m]))`
- RLS policy violations: `rate(rls_policy_violation_total[5m])`
- Webhook verification failures: spans `webhook.trips`, `webhook.cache` with event `webhook_verification_failed`

### Alert Conditions

- BYOK resolution failure rate > 5%
- Vault operation latency > 500ms p95
- RLS policy violations > 0
- Missing API keys for active users
- Repeated webhook verification failures (reason = `missing_secret_env` | `invalid_signature`)

## Incident Response

### API Key Compromise

1. Immediately revoke compromised key via `delete_user_api_key(userId, service)` RPC
2. Audit access logs for unauthorized usage (check telemetry spans `providers.resolve`)
3. Rotate affected API keys at provider (OpenAI dashboard, Anthropic console, etc.)
4. Reinsert new keys via BYOK UI or RPC

### Vault Security Breach

1. Assess breach scope and impact
2. Rotate all affected API keys at providers
3. Review and update access controls
4. Enhance monitoring and alerting
5. Execute full purge if required:

```sql
DELETE FROM vault.secrets WHERE name LIKE '%_api_key_%';
DELETE FROM public.api_keys;
UPDATE public.user_settings SET allow_gateway_fallback = true;
DELETE FROM public.api_gateway_configs;
```

### Webhook Incident

1. Rotate `HMAC_SECRET` env var and DB GUC atomically
2. Flush QStash signing keys if worker verification compromised
3. Replay missed events after verification is restored

### Service Outage

1. Check Supabase status page
2. Consider read-only mode if partial availability
3. Restore via PITR if corruption detected
