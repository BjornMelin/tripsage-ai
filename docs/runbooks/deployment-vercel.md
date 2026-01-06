# Deployment runbook: Vercel + Supabase + Upstash

## Prereqs

- Vercel account with project access
- Supabase project
- Upstash Redis and QStash
- BotID enabled in Vercel project

## Step 1: Configure integrations

1) Supabase integration

- Link Supabase project to Vercel project
- Ensure env vars are injected:
  - NEXT_PUBLIC_SUPABASE_URL
  - NEXT_PUBLIC_SUPABASE_ANON_KEY
  - SUPABASE_SERVICE_ROLE_KEY (server-only)

2) Upstash integration

- Inject:
  - UPSTASH_REDIS_REST_URL
  - UPSTASH_REDIS_REST_TOKEN
  - QSTASH_TOKEN
  - QSTASH_CURRENT_SIGNING_KEY
  - QSTASH_NEXT_SIGNING_KEY

3) AI provider keys

- Store as server-only env vars
- Do not prefix with NEXT_PUBLIC_

## Step 2: Configure build and runtime

- Node version: 20+
- pnpm version per repo standard
- Ensure `pnpm install --frozen-lockfile` works

## Step 3: DB migrations

- Use Supabase migrations in `supabase/migrations`
- Apply via Supabase CI or manual:
  - supabase db push (local)
  - or Supabase dashboard migrations (prod)

## Step 4: Verify production

- Hit /api/health
- Verify auth login works
- Verify chat streaming works
- Verify BotID protected endpoints reject bots
- Verify rate limit responses work

```text
Vercel Next.js deployment docs: https://vercel.com/docs/frameworks/full-stack/nextjs
Supabase Next.js quickstart: https://supabase.com/docs/guides/getting-started/quickstarts/nextjs
BotID docs: https://vercel.com/docs/botid/get-started
```
