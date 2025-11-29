# Quick Start

Canonical path to get TripSage running locally, with the minimal commands and the key knobs you need.

## Prerequisites

- **Runtime:** Node.js ≥24 and pnpm ≥9 (`npm install -g pnpm`)
- **Tooling:** Git
- **Accounts/keys:** Supabase project, Upstash Redis (and QStash if you test jobs), at least one model key (AI Gateway recommended)
- **Optional:** Docker (for containers), PostgreSQL local alt, Playwright browsers for E2E

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

# Frontend workspace
cd frontend && pnpm install && cd ..
```

## Configure

1) Copy env templates (root):

    ```bash
    cp .env.example .env
    cp .env.test.example .env.test
    ```

2) Set minimum variables to boot Next.js + tests:

```bash
# URLs
APP_BASE_URL=http://localhost:3000
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_SITE_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:3000

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret

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

# Maps (optional but required for map UI tests)
GOOGLE_MAPS_SERVER_API_KEY=your-server-key
NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY=your-browser-key
```

See [Environment Setup](env-setup.md) for full provider lists (Stripe, Resend, travel APIs, analytics) and a ready-to-run checklist.

## Run

```bash
cd frontend && pnpm dev
```

Visit <http://localhost:3000> and sign in via Supabase auth.

## Verify

```bash
cd frontend
pnpm biome:check && pnpm type-check
pnpm test:run
```

## Development Workflow

- **Lint/format/type:** `pnpm -C frontend biome:check`, `pnpm -C frontend biome:fix`, `pnpm -C frontend type-check`
- **Tests:** `pnpm -C frontend test:run` (or `--project=<name>`), `pnpm -C frontend test:e2e` for Playwright
- **Troubleshooting:** restart TS server, re-run `pnpm type-check`, verify env loaded (`env | grep SUPABASE`)

## Next Steps

- Standards: [docs/development/standards.md](standards.md)
- Zod Schema Guide: [docs/development/zod-schema-guide.md](zod-schema-guide.md)
- Testing: [docs/development/testing.md](testing.md)
- Observability: [docs/development/observability.md](observability.md)
- Troubleshooting: [docs/development/troubleshooting.md](troubleshooting.md)
