# TripSage Deployment Guide (Next.js + AI SDK v6)

This guide replaces the legacy FastAPI backend material. TripSage now runs as a server-first Next.js 16 app with AI SDK v6 route handlers.

## Prerequisites

- Node.js 20+ and pnpm 9+
- Supabase project (Postgres + GoTrue)
- Upstash Redis + QStash accounts
- Provider keys (OpenAI/Anthropic/xAI/OpenRouter or Vercel AI Gateway)

## Required environment variables

Copy the root `.env.example` to the target environment and fill the values (see links in `docs/developers/env-setup.md` for how to obtain each key):

- **Core URLs**: `APP_BASE_URL`, `NEXT_PUBLIC_APP_URL`, `NEXT_PUBLIC_SITE_URL`, `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_APP_NAME`, `NODE_ENV`
- **Supabase**: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET` (Dashboard → Settings → API)
- **Upstash/QStash**: `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`, `QSTASH_TOKEN`, `QSTASH_CURRENT_SIGNING_KEY`, `QSTASH_NEXT_SIGNING_KEY` (Upstash console)
- **AI providers**: `AI_GATEWAY_API_KEY`, `AI_GATEWAY_URL`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `XAI_API_KEY`, `EMBEDDINGS_API_KEY`
- **Maps/Weather**: `GOOGLE_MAPS_SERVER_API_KEY`, `NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY`, `OPENWEATHERMAP_API_KEY`
- **Payments**: `STRIPE_SECRET_KEY`, `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`
- **Email/Notifications**: `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `RESEND_FROM_NAME`, `HMAC_SECRET`
- **Travel APIs**: `DUFFEL_ACCESS_TOKEN`, `AMADEUS_CLIENT_ID`, `AMADEUS_CLIENT_SECRET`, `AMADEUS_ENV`

Keep root `.env.test.example` aligned for CI.

## Supabase setup

1) Create a project → copy project URL and anon key.  
2) Generate a service role key (Project Settings → API → Service role).  
3) Set JWT secret (same page) and paste into `SUPABASE_JWT_SECRET`.  
4) Apply SQL extensions/policies as needed.

## Upstash setup

- Redis: create a REST database → copy `REST URL` and `REST token` into `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN`.
- QStash: create a token and signing keys → set `QSTASH_TOKEN`, `QSTASH_CURRENT_SIGNING_KEY`, `QSTASH_NEXT_SIGNING_KEY`.

## Deployment

- **Vercel**: add the env vars above in Project Settings → Environment Variables; deploy from `main`.  
- **Self-host**: `pnpm install && pnpm build && pnpm start` with a fully populated `.env` (or `.env.production`).

## Observability

Telemetry is emitted via `@/lib/telemetry`. Configure OTLP export endpoints in `NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT` if collecting client traces; server spans rely on runtime exporters configured in code.

## Health and verification

- `pnpm biome:check && pnpm type-check && pnpm test:run` for local validation.
- Verify Supabase connectivity by running any server route that uses `getServerEnvVar("SUPABASE_SERVICE_ROLE_KEY")` (e.g., `/api/hooks/files`).
