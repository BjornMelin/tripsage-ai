# Manual Supabase Operations (TripSage)

> **Important**: Normal Supabase deployments, schema migrations, and edge function deployments are handled automatically through Vercel Supabase integration. This guide covers manual operations for initial project setup, troubleshooting, and scenarios where automated deployment is unavailable.

Audience: backend/infra developers. Command-first runbook for manual Supabase operations when Vercel integration isn't sufficient.

> **Note**: For general Supabase concepts, configuration patterns, and troubleshooting guidance, see [Supabase Configuration](supabase-configuration.md).

## Prerequisites

- Shell: `zsh`
- Tools: `deno >= 2.5`, `node >= 18`, `pnpm >= 8`, `jq`, `curl`
- Supabase CLI: `npx supabase@2.53.6 --version`
- Access: Supabase org permission to create/link projects

## A. One-time System Setup

```bash
# Verify tools
npx supabase@2.53.6 --version
node -v
pnpm -v
deno --version
```

## B. Create Supabase Project

The CLI cannot create hosted projects. Use the Supabase Dashboard:

1. Create project
   - Region: closest to app users
   - DB version: 17
2. Retrieve the Project Reference (e.g., `example-project-ref`)
3. Copy API keys: anon key, service role key

Required manual toggles (cannot be done from CLI):

- Realtime → Authorization: enable; Channels: Private only
- Authentication → URL Configuration:
  - Site URL: your app URL (e.g., `https://app.tripsage.com`)
  - Redirects: include `https://app.tripsage.com/auth/callback` and local dev callback

## C. Link Local Repo to Project

From repo root:

```bash
npx supabase@2.53.6 link --project-ref <PROJECT_REF> --debug
```

The CLI will write `supabase/.temp/profile` and `supabase/.temp/project-ref`.

## D. Validate supabase/config.toml (CLI v2-compatible)

Open `supabase/config.toml` and ensure:

- Remove deprecated `port` keys under `[realtime]`, `[storage]`, `[auth]`, `[edge_runtime]`
- `[db].major_version = 17`
- Disable unused OAuth providers to silence warnings until configured:

```toml
[auth.external.google]
enabled = false

[auth.external.github]
enabled = false
```

## E. Required Secrets (Project-wide)

Set only what you need; you can add others later. Use the anonymous and service keys from the Dashboard.

```bash
npx supabase@2.53.6 secrets set \
  SUPABASE_URL="https://<PROJECT_REF>.supabase.co" \
  SUPABASE_ANON_KEY="<anon>" \
  SUPABASE_SERVICE_ROLE_KEY="<service_role>"

# If using cache invalidation
npx supabase@2.53.6 secrets set \
  UPSTASH_REDIS_REST_URL="<url>" \
  UPSTASH_REDIS_REST_TOKEN="<token>"

# If sending emails from trip-notifications
npx supabase@2.53.6 secrets set RESEND_API_KEY="<resend>"

# Common webhook auth secret (used by functions/webhooks)
npx supabase@2.53.6 secrets set WEBHOOK_SECRET="<random-long-string>"
```

Run to review:

```bash
npx supabase@2.53.6 secrets list
```

## F. Database Migrations (Apply)

TripSage stores migrations in `supabase/migrations/`.

Nominal path:

```bash
npx supabase@2.53.6 db push --yes --debug
```

If you see "Remote migration versions not found in local migrations directory" with 8–12 digit versions (e.g., `20251027`), reconcile history:

```bash
# Inspect remote history
npx supabase@2.53.6 migration list --debug

# Mark a specific version reverted/applied to reconcile
npx supabase@2.53.6 migration repair --status reverted 20251027
# or
npx supabase@2.53.6 migration repair --status applied 20251028

# Retry push
npx supabase@2.53.6 db push --yes --debug
```

If a one-off migration was applied manually (e.g., webhook upserts), mark it applied:

```bash
npx supabase@2.53.6 migration repair --status applied 20251028
```

## G. Realtime Authorization Policies

Policies are created by migrations (e.g., `20251027_01_realtime_policies.sql`, helpers). Ensure Dashboard toggle is ON and channels are Private. Verify with a simple subscribe in the app; unauthorized users must be rejected by RLS.

## H. Edge Functions Deployment

TripSage includes these functions under `supabase/functions/`:

- `trip-notifications`
- `file-processing`
- `cache-invalidation` (uses Upstash Redis)
- `file-processor`

Each function folder contains a `deno.json` import map. Deploy:

```bash
npx supabase@2.53.6 functions deploy trip-notifications --project-ref <PROJECT_REF> --debug
npx supabase@2.53.6 functions deploy file-processing    --project-ref <PROJECT_REF> --debug
npx supabase@2.53.6 functions deploy cache-invalidation --project-ref <PROJECT_REF> --debug
npx supabase@2.53.6 functions deploy file-processor     --project-ref <PROJECT_REF> --debug
```

Notes:

- The Supabase bundler may run an older Deno that rejects `deno.lock` v5. If that occurs, rename `deno.lock -> deno.lock.v5` before deploy (locks stay in repo for dev).
- Logs:

```bash
npx supabase@2.53.6 functions list
npx supabase@2.53.6 functions logs cache-invalidation --tail
```

## I. Webhook Configuration (Optional)

TripSage includes an upsert migration to add default `webhook_configs` pointing to deployed functions. If not yet applied, run the SQL in Dashboard SQL editor (safe idempotent):

```sql
-- see supabase/migrations/20251028_01_update_webhook_configs.sql
-- sets trip_notifications, file_processing, cache_invalidation (is_active=false)
```

Activate when secrets are ready:

```sql
update public.webhook_configs set is_active = true
where name in ('trip_notifications','file_processing','cache_invalidation');
```

## J. Storage Buckets (Verify)

Buckets are provisioned by migration `202510271702_storage_infrastructure.sql`.

Verification SQL:

```sql
select id, name, public, file_size_limit from storage.buckets
where id in ('attachments','avatars','trip-images');
```

## K. End-to-End Verification

Minimal checks:

```bash
# Realtime: private channel subscribe from app (must use setAuth(access_token))

# Functions health
curl -i -X POST \
  "https://<PROJECT_REF>.supabase.co/functions/v1/cache-invalidation" \
  -H "Authorization: Bearer <service_role_or_user_jwt>" \
  -H "Content-Type: application/json" \
  -d '{"cache_type":"redis","keys":["test:key"]}'

# Logs
npx supabase@2.53.6 functions logs cache-invalidation --tail
```

## L. Rollback/Repair

```bash
# Mark a version reverted or applied, then push
npx supabase@2.53.6 migration repair --status reverted 20251027
npx supabase@2.53.6 db push --yes --debug
```

## Common Errors and Fixes

- **Migration mismatch**: Use `migration list` then `migration repair --status {applied|reverted} <version>`; retry `db push`
- **OAuth provider warnings**: Disable unused providers in `config.toml` until configured
- **Realtime join fails**: Ensure Realtime Authorization is enabled (Dashboard) and tokens are set via `supabase.realtime.setAuth(access_token)`
- **Edge Functions deploy lockfile error**: CLI bundler does not read `deno.lock` v5. Rename to `deno.lock.v5` for deploy

---

**Note**: For normal development and deployment workflows, use the automated Vercel Supabase integration. These manual operations are only needed for initial project setup or troubleshooting scenarios.
