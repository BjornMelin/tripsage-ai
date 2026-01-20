# Quick Start

Canonical path to get TripSage running locally, with the minimal commands and the key knobs you need.

## Prerequisites

- **Runtime:** Node.js ≥24 and pnpm ≥9 (`npm install -g pnpm`)
- **Tooling:** Git
- **Accounts/keys:** Supabase project, Upstash Redis (and QStash if you test jobs), at least one model key (AI Gateway recommended)
- **Optional:** Docker (required for local Supabase; optional if using a hosted Supabase project), Playwright browsers for E2E

## Stack Snapshot (for context)

- **Backend:** Next.js 16 server-first route handlers (TypeScript)
- **Frontend:** Next.js 16, React 19
- **Database:** Supabase Postgres + pgvector
- **Cache/Jobs:** Upstash Redis + QStash
- **AI:** Vercel AI SDK v6 (Gateway preferred; BYOK OpenAI/Anthropic/xAI/OpenRouter)
- **Auth:** Supabase JWT
- **State:** TanStack Query + Zustand
- **Testing:** Vitest (multi-project), Playwright E2E
- **Lint/Format:** Biome

## Install

```bash
git clone <repository-url>
cd tripsage-ai

# Install dependencies (at root)
pnpm install
```

## Configure

1) Copy env templates:

    ```bash
    cp .env.local.example .env.local
    cp .env.test.example .env.test
    ```

2) (Recommended) Start local Supabase:

    ```bash
    pnpm supabase:bootstrap
    pnpm supabase:status
    ```

    Copy the printed local values into `.env.local`:

    - `NEXT_PUBLIC_SUPABASE_URL`
    - `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (preferred) or `NEXT_PUBLIC_SUPABASE_ANON_KEY` (legacy)
    - `SUPABASE_SERVICE_ROLE_KEY` (use the `sb_secret_...` key from `pnpm supabase:status`)
    - (Recommended) `SUPABASE_JWT_SECRET` (use the `JWT_SECRET` value from `pnpm supabase:status`)

    Seed deterministic data for the scenario you’re working on:

    - `pnpm supabase:reset:dev`
    - `pnpm supabase:reset:e2e`
    - `pnpm supabase:reset:payments`
    - `pnpm supabase:reset:calendar`
    - `pnpm supabase:reset:edge-cases`

3) Set minimum variables to boot Next.js + tests:

```bash
# Put these in `.env.local` for Next.js local development.

# URLs
APP_BASE_URL=http://localhost:3000
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_SITE_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:3000

# Supabase
NEXT_PUBLIC_SUPABASE_URL=http://localhost:54321
# Set ONE of these public keys:
# - Preferred: NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY (sb_publishable_...)
# - Legacy: NEXT_PUBLIC_SUPABASE_ANON_KEY
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
# NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=sb_secret_...
SUPABASE_JWT_SECRET=local-dev-jwt-secret-min-32-chars-xxxxxxxxxxxxxxxx

# Redis / QStash
UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-redis-token
QSTASH_TOKEN=your-qstash-token
QSTASH_CURRENT_SIGNING_KEY=your-current-signing-key
QSTASH_NEXT_SIGNING_KEY=your-next-signing-key

# AI (choose one: Gateway or BYOK providers)
AI_GATEWAY_API_KEY=your-gateway-key
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
XAI_API_KEY=your-xai-key
OPENROUTER_API_KEY=your-openrouter-key

# RAG reranking (optional; if unset, reranking degrades to no-op)
TOGETHER_AI_API_KEY=your-togetherai-key

# Embeddings note:
# - If AI_GATEWAY_API_KEY or OPENAI_API_KEY is set, RAG/memory use real embeddings (`openai/text-embedding-3-small`, 1536-d).
# - If unset, the app uses a deterministic 1536-d fallback so local dev + tests remain runnable (not semantically meaningful).

# Maps (optional but required for map UI tests)
GOOGLE_MAPS_SERVER_API_KEY=your-server-key
NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY=your-browser-key
```

See [Environment Setup](env-setup.md) for full provider lists (Stripe, Resend, travel APIs, analytics) and a ready-to-run checklist.
For a reproducible local Supabase + seeded RAG smoke test, see [Local Supabase + RAG E2E](local-supabase-rag-e2e.md).

## Run

```bash
pnpm dev
```

Visit <http://localhost:3000> and sign in via Supabase auth.

## Verify

```bash
pnpm biome:check && pnpm type-check
pnpm test
```

## Build

```bash
pnpm build
```

## E2E (Playwright)

TripSage’s Playwright E2E suite starts its own dev server and uses a mock Supabase Auth HTTP server by default (it does not require a running local Supabase instance).

```bash
pnpm exec playwright install chromium
pnpm test:e2e:chromium
```

If you want to run the app against a real local Supabase database for manual E2E/QA (recommended for RAG/attachments), use:

```bash
pnpm supabase:reset:dev
pnpm dev
```

## Development Workflow

- **Lint/format/type:** `pnpm biome:check`, `pnpm biome:fix`, `pnpm type-check`
- **Tests:** `pnpm test` (or `--project=<name>`), `pnpm test:e2e:chromium` for Playwright (or `pnpm test:e2e` for the full browser matrix)
- **Troubleshooting:** restart TS server, re-run `pnpm type-check`, verify env loaded (`env | grep SUPABASE`)

## Next Steps

- Standards: [docs/development/standards/standards.md](../standards/standards.md)
- Zod Schema Guide: [docs/development/standards/zod-schema-guide.md](../standards/zod-schema-guide.md)
- Testing: [docs/development/testing/testing.md](../testing/testing.md)
- Observability: [docs/development/backend/observability.md](../backend/observability.md)
- Troubleshooting: [docs/development/core/troubleshooting.md](troubleshooting.md)
