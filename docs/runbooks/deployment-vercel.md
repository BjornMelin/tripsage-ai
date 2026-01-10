# Deployment runbook: Vercel + Supabase + Upstash

## Prereqs

- Vercel account with project access
- Supabase project
- Upstash Redis and QStash
- BotID enabled in Vercel project
- Vercel OIDC enabled for the project (required by `botid/server` checks)
- Node.js 24.x (per repo engines) and pnpm (per `packageManager`)

## Step 1: Configure integrations

1) Supabase integration

- Link Supabase project to Vercel project
- Ensure env vars are injected:
  - NEXT_PUBLIC_SUPABASE_URL
  - NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY (preferred) or NEXT_PUBLIC_SUPABASE_ANON_KEY (legacy)
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

- Node version: 24.x
- pnpm version per repo `packageManager`
- Ensure `pnpm install --frozen-lockfile` works

## Step 3: Proxy, CSP, and security headers

- `src/proxy.ts` is the single canonical place for CSP + baseline security headers.
- Proxy generates a per-request nonce, sets `x-nonce` on the request, and mirrors the CSP header onto the response.
- With Cache Components enabled, ensure all request-bound Dynamic APIs (like `headers()`) are only awaited under `<Suspense>` boundaries. The nonce is read in `src/app/layout.tsx` inside `AppShell` under `<Suspense fallback={null}>`.
- Production CSP is intentionally compatible with Partial Prerendering (PPR): it does **not** rely on `strict-dynamic` for framework scripts, and it allowlists only the minimal Next.js inline bootstrap snippet hash needed for runtime.

## Step 4: DB migrations

- Use Supabase migrations in `supabase/migrations`
- Apply via Supabase CI or manual:
  - supabase db push (local)
  - or Supabase dashboard migrations (prod)

## Step 5: Verify production

- Hit /api/health
- Verify auth login works
- Verify chat streaming works
- Verify BotID protected endpoints reject bots
- Verify rate limit responses work
- Verify CSP is present on HTML responses (and that third-party scripts include a nonce)
- If a Next.js upgrade changes an internal inline bootstrap snippet, update the allowlisted hash in `src/proxy.ts` and confirm `pnpm exec playwright test -c playwright.prod.config.ts` passes before deploying.

```text
Vercel Next.js deployment docs: https://vercel.com/docs/frameworks/full-stack/nextjs
Supabase Next.js quickstart: https://supabase.com/docs/guides/getting-started/quickstarts/nextjs
BotID docs: https://vercel.com/docs/botid/get-started
```
