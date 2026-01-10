# Local development runbook (Next.js + Supabase SSR + BotID + Upstash)

## Prereqs

- Node.js 24.x (per `package.json` `engines`)
- pnpm (per `package.json` `packageManager`)
- Optional but recommended for full functionality:
  - Supabase project (or local Supabase)
  - Upstash Redis (RateLimit)

## Environment setup

- Copy `.env.example` → `.env` and populate required variables.
- See: `docs/development/core/env-setup.md`

## Run the app

```bash
pnpm install
pnpm dev
```

## Proxy / CSP / security headers

- `src/proxy.ts` is the single canonical place for:
  - nonce-based CSP (`Content-Security-Policy`)
  - baseline security headers
  - Supabase SSR cookie refresh (session maintenance)
- Nonce-based CSP requires **request-time rendering** (nonces are per-request).
- With Cache Components enabled, `src/app/layout.tsx` enforces request-time rendering via `await connection()` inside a `<Suspense>` boundary so prerendering cannot emit nonce-dependent output.
- If adding third-party scripts/components, pass the nonce from the request header:
  - read `x-nonce` via `headers()` (inside a `<Suspense>` boundary) and forward it to components that support a `nonce` prop.

## BotID (local behavior)

- BotID is initialized client-side in `src/instrumentation-client.ts` using `initBotId()`.
- The canonical client `protect` rules live in `src/config/botid-protect.ts` and must stay aligned with server-side `botId: true` routes.
- Local development behavior:
  - BotID classification is not meaningful locally (typically `isBot: false`).
  - Validate BotID enforcement via unit tests (mock `botid/server`) and Vercel preview deployments for real detection.
  - `pnpm build` may log a "Possible misconfiguration of Vercel BotId" warning outside Vercel (no BotID request headers are present during build-time prerendering).

## Upstash rate limiting (local)

- Route handlers use `withApiGuards({ rateLimit })` which enforces Upstash RateLimit.
- Many sensitive routes default to **fail-closed** when Upstash is unavailable (returning `503 rate_limit_unavailable`).
- For a smooth local dev experience, set:
  - `UPSTASH_REDIS_REST_URL`
  - `UPSTASH_REDIS_REST_TOKEN`

## Local quality gates (required before pushing)

```bash
pnpm biome:fix
pnpm type-check
pnpm test:affected
```

## E2E (Playwright)

```bash
pnpm test:e2e:chromium
```

Playwright runs a local dev server via `scripts/e2e-webserver.mjs` and sets `E2E=1` for test-only helpers.
