# Supabase Reproducible Deployment (TripSage)

This document provides a single pass, reproducible sequence to provision all database infrastructure, deploy Edge Functions, set secrets, and validate the environment for TripSage.

## A. One-time system setup

```bash
# Verify tools
npx supabase@2.53.6 --version
node -v
pnpm -v
deno --version
```

## B. Link project

```bash
npx supabase@2.53.6 link --project-ref <PROJECT_REF> --debug
```

## C. Secrets (minimal)

```bash
npx supabase@2.53.6 secrets set \
  SUPABASE_URL="https://<PROJECT_REF>.supabase.co" \
  SUPABASE_ANON_KEY="<anon>" \
  SUPABASE_SERVICE_ROLE_KEY="<service_role>"

# Optional
npx supabase@2.53.6 secrets set UPSTASH_REDIS_REST_URL="<url>" UPSTASH_REDIS_REST_TOKEN="<token>"
npx supabase@2.53.6 secrets set RESEND_API_KEY="<resend>"
npx supabase@2.53.6 secrets set WEBHOOK_SECRET="<webhook_secret>"
```

## D. Apply migrations

```bash
npx supabase@2.53.6 db push --yes --debug
```

If mismatch errors appear (8–12 digit migration IDs), reconcile:

```bash
npx supabase@2.53.6 migration list --debug
npx supabase@2.53.6 migration repair --status applied 20251028
npx supabase@2.53.6 db push --yes --debug
```

## E. Realtime Authorization (Dashboard)

- Enable Authorization; set channels to Private only.

## F. Deploy Edge Functions

```bash
npx supabase@2.53.6 functions deploy trip-notifications --project-ref <PROJECT_REF> --debug
npx supabase@2.53.6 functions deploy file-processing    --project-ref <PROJECT_REF> --debug
npx supabase@2.53.6 functions deploy cache-invalidation --project-ref <PROJECT_REF> --debug
npx supabase@2.53.6 functions deploy file-processor     --project-ref <PROJECT_REF> --debug
```

If the bundler errors on `deno.lock` version, rename `deno.lock -> deno.lock.v5` and redeploy.

## G. Webhook endpoints (optional)

Migrate or apply SQL to insert `webhook_configs` (inactive by default). Activate only after `WEBHOOK_SECRET` is set:

```sql
update public.webhook_configs set is_active = true
where name in ('trip_notifications','file_processing','cache_invalidation');
```

## H. Verify

```bash
npx supabase@2.53.6 functions list
npx supabase@2.53.6 functions logs cache-invalidation --tail

curl -i -X POST \
  "https://<PROJECT_REF>.supabase.co/functions/v1/cache-invalidation" \
  -H "Authorization: Bearer <service_role_or_user_jwt>" \
  -H "Content-Type: application/json" \
  -d '{"cache_type":"redis","keys":["test:key"]}'
```

## I. Rollback/repair

```bash
# Mark a version reverted or applied, then push
npx supabase@2.53.6 migration repair --status reverted 20251027
npx supabase@2.53.6 db push --yes --debug
```
