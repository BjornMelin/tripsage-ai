# TripSage Operators Reference (frontend-only)

This supersedes legacy backend notes. All runtime is Next.js 16 with AI SDK v6 route handlers.

## Prerequisites

- Node.js 20+, pnpm 9+
- Supabase project (URL, anon key, service role key, JWT secret)
- Upstash Redis + QStash
- Model provider keys or Vercel AI Gateway

## Environment variables (align with `.env.example`)

- Core: `NODE_ENV`, `APP_BASE_URL`, `NEXT_PUBLIC_APP_URL`, `NEXT_PUBLIC_SITE_URL`, `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_APP_NAME`, `NEXT_PUBLIC_BASE_PATH`, `NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT`
- Supabase: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `DATABASE_URL` (optional local Postgres)
- Upstash/QStash: `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`, `QSTASH_TOKEN`, `QSTASH_CURRENT_SIGNING_KEY`, `QSTASH_NEXT_SIGNING_KEY`
- AI providers: `AI_GATEWAY_API_KEY`, `AI_GATEWAY_URL`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `XAI_API_KEY`, `EMBEDDINGS_API_KEY`
- Maps/Weather: `GOOGLE_MAPS_SERVER_API_KEY`, `NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY`, `OPENWEATHERMAP_API_KEY`
- Payments: `STRIPE_SECRET_KEY`, `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`
- Email/notifications: `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `RESEND_FROM_NAME`, `HMAC_SECRET`, `COLLAB_WEBHOOK_URL` (optional)
- Travel APIs: `DUFFEL_ACCESS_TOKEN`, `DUFFEL_API_KEY` (fallback), `AMADEUS_CLIENT_ID`, `AMADEUS_CLIENT_SECRET`, `AMADEUS_ENV`, `GOOGLE_MAPS_API_KEY`
- Analytics (optional): `GOOGLE_ANALYTICS_ID`, `MIXPANEL_TOKEN`, `POSTHOG_HOST`, `POSTHOG_KEY`

## Start and verify

```bash
cp .env.example .env
pnpm install
pnpm dev
```

- Run checks: `pnpm biome:check && pnpm type-check && pnpm test:run`

## Notes

- No legacy Python backend remains.
- Rate limiting and caching require Upstash REST credentials; without them routes will operate without limits.
- QStash signing keys are mandatory for webhook verification in production.
