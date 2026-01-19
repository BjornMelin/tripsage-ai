# TripSage Deployment Guide (Next.js + AI SDK v6)

This guide replaces the legacy FastAPI backend material. TripSage now runs as a server-first Next.js 16 app with AI SDK v6 route handlers.

## Prerequisites

- Node.js 24+ and pnpm 9+
- Supabase project (Postgres + GoTrue)
- Upstash Redis + QStash accounts (HTTP/REST clients only; no TCP Redis clients)
- Provider keys (OpenAI/Anthropic/xAI/OpenRouter or Vercel AI Gateway)

## Required environment variables

Copy the root `.env.example` to the target environment and fill the values (see links in `docs/development/core/env-setup.md` for how to obtain each key):

- **Core URLs**: `APP_BASE_URL`, `NEXT_PUBLIC_APP_URL`, `NEXT_PUBLIC_SITE_URL`, `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_APP_NAME`, `NODE_ENV`
- **Supabase**: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (preferred) or `NEXT_PUBLIC_SUPABASE_ANON_KEY` (legacy), `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET` (Dashboard → Settings → API)
- **Upstash/QStash**: `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`, `QSTASH_TOKEN`, `QSTASH_CURRENT_SIGNING_KEY`, `QSTASH_NEXT_SIGNING_KEY` (Upstash console)
- **AI providers**: `AI_GATEWAY_API_KEY`, `AI_GATEWAY_URL`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `XAI_API_KEY`, `EMBEDDINGS_API_KEY`
- **Feature flags**: `ENABLE_AI_DEMO` (set to `"true"` to enable demo routes)
- **Telemetry**: `TELEMETRY_HASH_SECRET` (required in production; enables stable hashed identifiers in spans), `TELEMETRY_AI_DEMO_KEY` (required only if enabling `/api/telemetry/ai-demo`)
- **Maps/Weather**: `GOOGLE_MAPS_SERVER_API_KEY`, `NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY`, `OPENWEATHERMAP_API_KEY`
- **Payments**: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`
- **Email/Notifications**: `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `RESEND_FROM_NAME`, `HMAC_SECRET`
- **Travel APIs**: `DUFFEL_ACCESS_TOKEN`, `AMADEUS_CLIENT_ID`, `AMADEUS_CLIENT_SECRET`, `AMADEUS_ENV`

Keep root `.env.test.example` aligned for CI.

> Tip: keep runtime-only secrets (service role, gateway keys) server-side; never expose them via `NEXT_PUBLIC_*`.

## Supabase setup

1) Create a project → copy project URL and public key.  
2) Generate a service role key (Project Settings → API → Service role).  
3) Set JWT secret (same page) and paste into `SUPABASE_JWT_SECRET`.  
4) Apply SQL extensions/policies as needed.
5) Link and push migrations before production deploys:

```bash
make supa.link PROJECT_REF=<your-ref>   # one-time
make supa.db.push                       # apply supabase/migrations/* to remote
```

## Upstash setup

- Redis: create a REST database → copy `REST URL` and `REST token` into `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN`.
- QStash: create a token and signing keys → set `QSTASH_TOKEN`, `QSTASH_CURRENT_SIGNING_KEY`, `QSTASH_NEXT_SIGNING_KEY`.

## Deployment

- **Canonical: Vercel (Next.js App Router)**  
  - Default runtime: **Node.js**. Use Edge only for stateless/public paths that do not require Supabase SSR cookies.  
  - Set Environment Variables in Project Settings for `production` and `preview`.  
  - Build command: `pnpm build`; Output: `Next.js`.  
- **Self-host (optional)**: `pnpm install && pnpm build && pnpm start` with a fully populated `.env` (or `.env.production`). Provide your own reverse proxy/TLS and process manager.

### Vercel configuration (`vercel.json`)

The `vercel.json` file configures function settings:

```json
{
  "functions": {
    "src/app/api/**/route.*": {
      "maxDuration": 60
    }
  }
}
```

**Why no `regions` property?** Vercel's function config schema does not support `regions` at the function level—including it causes deployment errors. For regional pinning in Next.js App Router, use route segment config exports instead:

```typescript
// In any route.ts file
export const preferredRegion = 'iad1'  // or ['iad1', 'sfo1'] for multi-region
```

Alternatively, configure the default function region in Vercel Dashboard → Project → Settings → Functions.

## Observability

Telemetry is emitted via `@/lib/telemetry`. Configure OTLP export endpoints in `NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT` for client traces; server spans export via OTLP/HTTP and can be scraped by Jaeger/Tempo/OTel Collector. Avoid `console.*` in server code—use `createServerLogger()` from `@/lib/telemetry/logger` and span events instead.

## Health and verification

- `pnpm biome:check && pnpm type-check && pnpm test` for local validation.
- Verify Supabase connectivity by running any server route that uses `getServerEnvVar("SUPABASE_SERVICE_ROLE_KEY")` (e.g., `/api/hooks/files`).
