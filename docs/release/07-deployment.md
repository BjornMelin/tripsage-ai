# TripSage AI — Deployment (v1.0.0)

## Platforms

- Web: Vercel (Next.js)
- Data/Auth/Storage: Supabase
- Rate limiting/queues: Upstash (Redis/QStash)

## Required Env Vars (names only)

Populate in `.env.local` for dev and Vercel project env for deploy. **Do not commit values.**

Reference templates:

- `.env.example` (local/dev template)
- `.env.test.example` (test template)

Minimum required for a production deploy (strict):

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` (or `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` if you prefer)
- `SUPABASE_JWT_SECRET`
- `TELEMETRY_HASH_SECRET`

Common operational env vars (non-exhaustive, names only):

- Core URLs: `APP_BASE_URL`, `NEXT_PUBLIC_SITE_URL`, `NEXT_PUBLIC_API_URL`
- Supabase: `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`
- Upstash Redis: `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`
- Upstash QStash: `QSTASH_TOKEN`, `QSTASH_CURRENT_SIGNING_KEY`, `QSTASH_NEXT_SIGNING_KEY`
- AI gateway/providers: `AI_GATEWAY_API_KEY`, `AI_GATEWAY_URL`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, `XAI_API_KEY`, `EMBEDDINGS_API_KEY`
- Search/crawl: `FIRECRAWL_API_KEY`, `FIRECRAWL_BASE_URL`
- Maps/weather: `GOOGLE_MAPS_SERVER_API_KEY`, `NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY`, `OPENWEATHERMAP_API_KEY`
- Payments: `STRIPE_SECRET_KEY`, `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`
- Email: `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `RESEND_FROM_NAME`
- Security: `HMAC_SECRET`, `MFA_BACKUP_CODE_PEPPER`, `TELEMETRY_AI_DEMO_KEY`, `COLLAB_WEBHOOK_URL`
- Flags: `ENABLE_AI_DEMO`, `DEBUG`, `ANALYZE`

## Deployment Checklist

- Build passes locally: `pnpm build`
- E2E passes locally (Chromium): `pnpm test:e2e:chromium` (fresh machine: `pnpm exec playwright install chromium`)
- Supabase migrations applied
- RLS policies reviewed and enabled
- Upstash keys configured (rate limiting, QStash signing)

## Vercel

Notes:

- `vercel.json` currently sets `"git.deploymentEnabled": false`. Decide whether v1.0.0 should enable automatic Git deployments (Vercel Project Settings can override).
- Next.js `output: "standalone"` is enabled in `next.config.ts`.

Recommended Vercel setup:

- Framework preset: Next.js
- Build command: `pnpm build`
- Install command: `pnpm install --frozen-lockfile` (optional but recommended)
- Output: handled by Next (standalone server in `.next/standalone`)

## Supabase

Source of truth lives in `supabase/migrations/`.

Local:

- `supabase start`
- `supabase db reset --debug`

Prod:

- `supabase link --project-ref <your-project-ref>`
- `supabase db push`

Database → Vercel webhooks are documented in `docs/operations/supabase-webhooks.md`.

## References (full URLs)

- Next.js deployment docs: https://nextjs.org/docs/app/building-your-application/deploying
- Vercel Next.js docs: https://vercel.com/docs/frameworks/nextjs
- Supabase docs: https://supabase.com/docs
- Upstash docs: https://upstash.com/docs
- Supabase CLI: https://supabase.com/docs/guides/cli
