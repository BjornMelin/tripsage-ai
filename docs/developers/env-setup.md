# Environment Setup Guide (local development)

Copy the root `.env.example` to `.env`, then follow the checklists below to populate every variable. Copy root `.env.test.example` to `.env.test` for local/CI test runs. All service-specific env files are derived from the root templates.

## Core & Supabase

- Core URLs (all usually `http://localhost:3000` during dev):
  - `APP_BASE_URL`
  - `NEXT_PUBLIC_APP_URL`
  - `NEXT_PUBLIC_SITE_URL`
  - `NEXT_PUBLIC_API_URL`
- Supabase (Dashboard → Settings → API):
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `SUPABASE_JWT_SECRET`
  - Console: <https://supabase.com/dashboard>

## Upstash (Redis + QStash)

- Redis REST (caching/rate-limit):
  - `UPSTASH_REDIS_REST_URL` (REST URL)
  - `UPSTASH_REDIS_REST_TOKEN` (REST token)
  - Console: <https://console.upstash.com/redis>
- QStash (jobs/webhooks):
  - `QSTASH_TOKEN`
  - `QSTASH_CURRENT_SIGNING_KEY`
  - `QSTASH_NEXT_SIGNING_KEY`
  - Console: <https://console.upstash.com/qstash>

## AI providers / Gateway

- Vercel AI Gateway:
  - `AI_GATEWAY_API_KEY`
  - `AI_GATEWAY_URL` (defaults to `https://ai-gateway.vercel.sh/v1`)
  - Dashboard: <https://vercel.com/ai-gateway>
- Direct providers:
  - `OPENAI_API_KEY` — <https://platform.openai.com/api-keys>
  - `ANTHROPIC_API_KEY` — <https://console.anthropic.com>
  - `XAI_API_KEY` — <https://console.x.ai>
  - `OPENROUTER_API_KEY` — <https://openrouter.ai/keys>
- Optional:
  - `EMBEDDINGS_API_KEY` (internal/private embeddings route)

## Search / crawling

- `FIRECRAWL_API_KEY`
- `FIRECRAWL_BASE_URL` (optional; defaults to hosted API)
- Docs: <https://docs.firecrawl.dev/getting-started/api-key>

## Maps / Weather

- Google Maps Platform (same credentials page: <https://console.cloud.google.com/google/maps-apis/credentials>)
  - `GOOGLE_MAPS_SERVER_API_KEY` (server-restricted: Places/Geocoding/Routes)
  - `NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY` (browser, referrer-restricted)
- Weather:
  - `OPENWEATHERMAP_API_KEY` — <https://home.openweathermap.org/api_keys>

## Payments

- Stripe keys (<https://dashboard.stripe.com/apikeys>):
  - `STRIPE_SECRET_KEY`
  - `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`

## Email / notifications

- Resend (<https://resend.com/api-keys>):
  - `RESEND_API_KEY`
  - `RESEND_FROM_EMAIL`
  - `RESEND_FROM_NAME`
- Webhook signing:
  - `HMAC_SECRET` (generate a strong random string)

## Travel APIs

- Duffel (<https://app.duffel.com/developers>):
  - `DUFFEL_ACCESS_TOKEN` (preferred)
  - `DUFFEL_API_KEY` (fallback)
- Amadeus Self-Service:
  - <https://developers.amadeus.com/get-started>
  - Variables: `AMADEUS_CLIENT_ID`, `AMADEUS_CLIENT_SECRET`, `AMADEUS_ENV` (`test`|`production`)
- Google Places (New):
  - Enable Places API (New) + Photos in Google Cloud Console
  - Uses the same Google Maps Platform API keys (no separate Places API key required)
  - Server-side: `GOOGLE_MAPS_SERVER_API_KEY` (IP+API restricted for Places/Geocoding/Routes)
  - Browser/client-side: `NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY` (referrer-restricted)

## Optional analytics

- `GOOGLE_ANALYTICS_ID` (GA4), `MIXPANEL_TOKEN`, `POSTHOG_HOST`, `POSTHOG_KEY` — create per-provider dashboards; safe to leave empty locally.

## Ready-to-run checklist

- [ ] `.env` copied from root `.env.example`
- [ ] `.env.test` copied from root `.env.test.example` for local/CI test runs
- [ ] Supabase URL + anon key + service role key present
- [ ] Upstash Redis REST URL + token present
- [ ] QStash token + signing keys present
- [ ] At least one model provider key (OpenAI/Anthropic/xAI/OpenRouter or `AI_GATEWAY_API_KEY`)
- [ ] Google Maps server key set if using maps; browser key for client maps
- [ ] Stripe keys set if payment flows are exercised
- [ ] Resend key and from info set if email notifications are needed
- [ ] Travel providers set if flights/hotels features are tested

## Quick verification

```bash
pnpm biome:check && pnpm type-check && pnpm test:run
```

If startup validation fails, re-check required variables above before debugging code.
