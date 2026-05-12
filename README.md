# 🌟 TripSage AI

[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org)
[![AI SDK v6](https://img.shields.io/badge/Vercel%20AI%20SDK-v6-blue.svg)](https://ai-sdk.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-6-blue.svg)](https://typescriptlang.org)
[![Supabase](https://img.shields.io/badge/Supabase-SSR-3fcf8e?logo=supabase)](https://supabase.com)
[![Upstash](https://img.shields.io/badge/Upstash-Redis%20%7C%20QStash-00E9A3?logo=upstash)](https://upstash.com)
[![Vercel](https://img.shields.io/badge/Vercel-AI%20Gateway-black?logo=vercel)](https://vercel.com)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

<!-- markdownlint-disable MD033 -->
<div align="center">

## **Next-Generation AI-Powered Travel Planning Platform**

**Modern Architecture** • **Agentic Multi-Agent Search** • **Configurable Providers** • **Open-Source**

</div>
<!-- markdownlint-enable MD033 -->

---

TripSage AI is a travel planning platform that combines the power of modern
AI agents with rich AI SDK v6 tools and all-in-one travel services.

## ✨ Key Features

### AI & Intelligence

- **AI Gateway + BYOK Routing**: Vercel AI Gateway for app-owned OpenAI profiles, direct user BYOK for OpenAI/OpenRouter/Anthropic/xAI, and encrypted key storage
- **Agentic Tool Orchestration**: 15+ production-ready tools via AI SDK v6 with Zod validation—flights (Duffel), accommodations, weather, maps, planning, and memory
- **Hybrid RAG Pipeline**: Vector similarity search with Supabase pgvector + keyword fusion, with Together.ai and Mixedbread reranking for retrieval accuracy
- **Structured Outputs**: Schema-first LLM responses with `generateText` + `Output.object` for deterministic parsing and type-safe validation
- **Streaming Intelligence**: Real-time SSE streaming with interleaved tool calls and generative UI components

### Data & Infrastructure

- **Supabase PostgreSQL + pgvector**: Managed database with HNSW indexes for semantic search, embeddings storage, and vector similarity queries
- **Supabase Auth & Vault**: Server-side authentication with SSR clients (`@supabase/ssr`), encrypted BYOK secrets in Vault with RLS-gated access
- **Supabase Realtime**: Private channels with Row Level Security for multi-user collaboration, presence tracking, and broadcast events
- **Supabase Storage**: File uploads with signed URL access, metadata persistence, and server-enforced access control

### Performance & Scalability

- **Upstash Redis**: Serverless HTTP Redis for sub-10ms global caching, sliding-window rate limiting, and deduplication keys
- **Upstash QStash**: Webhook-driven background jobs with signature verification, Redis idempotency gates, and batch processing (memory sync, async tasks)
- **Vercel Runtime Architecture**: Next.js 16 route handlers, Vercel CLI prebuilt promotion, and global CDN delivery for low-latency responses
- **React Compiler**: Automatic memoization and zero-overhead reactive rendering for optimal performance

### Security & Compliance

- **Zero-Trust Architecture**: BYOK keys never touch client; server-only routes with `"server-only"` imports and dynamic execution
- **Row Level Security**: Supabase RLS policies enforce per-user data isolation; security-definer RPCs guard Vault access
- **Rate Limiting**: Upstash Ratelimit with tiered budgets (40 req/min streaming, 20 req/min validation) per user/IP
- **OpenTelemetry**: Distributed tracing with PII redaction, span instrumentation, and Trace Drains for observability without data leakage
- **Tool Approval Flows**: Sensitive operations (bookings, payments) pause streaming and require explicit user consent

### Modern Frontend

- **Next.js 16 + React 19**: App Router with RSC-first architecture, Server Components by default, React Compiler enabled
- **TypeScript 6**: Strict mode with end-to-end type safety, Zod schemas as single source of truth
- **AI SDK v6 Native**: TypeScript-native provider resolution, streaming, tool calling, and structured outputs

## Quick Start

### Prerequisites

- **Node.js 24.x** (see `.nvmrc`) with **pnpm 10.x** (see `package.json#packageManager`)
- **PostgreSQL 15+** (or Supabase account)
- **Upstash Redis** for caching (via Vercel integration)

### Installation

```bash
# Clone the repository
git clone https://github.com/BjornMelin/tripsage-ai.git
cd tripsage-ai

# Install dependencies
pnpm install --frozen-lockfile            # Install Node.js dependencies
cp .env.local.example .env.local          # Configure environment

# Start development server (includes API routes)
pnpm dev                                  # Next.js app + API routes (port 3000)
```

### Verification

```bash
# Frontend access
open http://localhost:3000
```

## Architecture

Single-runtime, server-first stack optimized for edge deployment:

- **Backend & UI**: Next.js 16 App Router (React 19) with Vercel AI SDK v6 RSC/actions and React Compiler
- **AI Routing**: Vercel AI Gateway for app-owned OpenAI profiles with opt-in team fallback, plus BYOK support via Supabase Vault
- **Database & Auth**: Supabase PostgreSQL with pgvector (HNSW indexes), SSR clients (`@supabase/ssr`), Realtime channels, Storage buckets
- **Cache & Rate Limiting**: Upstash Redis (HTTP) for serverless caching and Upstash Ratelimit for sliding-window throttling
- **Background Jobs**: Upstash QStash for webhook-driven async tasks with idempotency guarantees
- **Observability**: OpenTelemetry with Vercel Trace Drains, span instrumentation, and PII redaction

## Development

```bash
# Frontend / API (single app at root)
pnpm install --frozen-lockfile
pnpm dev            # Next.js dev server (includes API routes)
pnpm type-check
pnpm biome:fix      # Format/lint (CI enforces clean diffs)
pnpm test           # Vitest
pnpm exec playwright install chromium  # one-time browser install (fresh machine)
pnpm test:e2e:chromium                # Playwright (Chromium-only; recommended local default)
pnpm test:e2e                         # Playwright (all configured browsers)

# Supabase tooling (optional)
make supa.link PROJECT_REF=...
make supa.db.push
```

If `pnpm` is not already on your `PATH`, use `corepack pnpm ...` instead of `npx pnpm ...`. The repo root `.npmrc` intentionally contains pnpm-only config, and `npx` will make npm parse it and print warnings. You can also run `corepack enable` once to install the `pnpm` shim so `pnpm` is available directly on your `PATH`, which matters for tools like pre-commit hooks and CI scripts that invoke `pnpm` without the `corepack` prefix.

### Observability (OpenTelemetry)

Server-side tracing is registered via `src/instrumentation.ts` using `@vercel/otel`. Client-side tracing is initialized via `TelemetryProvider` (mounted from `src/app/layout.tsx`) and exports browser spans with OTLP/HTTP.

Local tracing (Collector + Jaeger):

```bash
docker compose up -d otel-collector jaeger
open http://localhost:16686
```

Enable browser tracing (optional):

```bash
# Either is accepted (client normalizes to `/v1/traces`)
NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
# or
NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318/v1/traces
# (also accepted)
NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318/v1/traces/
```

To disable browser tracing in production, leave `NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT` unset.

### Formatting enforcement

Run `pnpm biome:fix` before committing. CI runs `pnpm biome:fix` and then checks for a clean working tree with `git diff --exit-code`, so any formatting changes produced locally will fail CI if not committed.

## Project Structure

```text
tripsage-ai/
├── src/             # Next.js 16 + AI SDK v6 source code
├── public/          # Static assets
├── e2e/             # Playwright E2E tests
├── supabase/        # Supabase migrations/config
├── docker/          # OTEL/Jaeger compose
├── .github/         # CI/CD
├── package.json     # Node.js dependencies
└── Makefile         # Supabase ops shortcuts
```

## Conventions

- Server-first: Route handlers and Server Actions own data fetching and AI calls. Use `convertToModelMessages`, `streamText`, `toUIMessageStreamResponse`, and Zod v4 validation.
- Auth/DB: `@supabase/ssr` only; no auth-helpers.
- Cache/jobs: Upstash HTTP clients only (`Redis.fromEnv`, QStash SDK).
- Logging: OTEL exporters; no `console.log` in server code.
- Tests: Vitest/Playwright only (no pytest/ruff/uv).

---

## Deployment

Production deploys use the Vercel CLI workflow in
[docs/runbooks/deployment-vercel.md](docs/runbooks/deployment-vercel.md):

```bash
pnpm deploy:check-env
vercel pull --yes --environment=production
vercel build --prod
vercel deploy --prebuilt --prod --skip-domain --archive=tgz --yes
pnpm deploy:smoke -- --url "$DEPLOYMENT_URL"
vercel promote "$DEPLOYMENT_URL" --yes --timeout=5m
```

Docker compose files in `docker/` are local observability/dev helpers, not the
production deploy authority.

### Environment Configuration

`scripts/verify-production-env.mjs` is the deploy-time source of truth. It
validates core app origins, Supabase SSR/Vault, Upstash Redis/QStash, security
secrets, BYOK health checks, and feature-aware provider groups for Stripe,
Resend, Amadeus, Duffel, Expedia, analytics, and AI providers.

For local setup, start from `.env.local.example`. For production, run
`pnpm deploy:check-env` before `vercel build`.

---

## 🔌 API Overview

### Core Route Groups

```bash
GET  /api/health                  # Public runtime health
POST /api/chat                    # AI SDK v6 UI message stream
POST /api/flights/search          # Flight search
GET  /api/trips/suggestions       # AI-powered trip suggestions
POST /api/keys/validate           # BYOK provider validation
GET  /api/health/byok             # Operator-only BYOK health probe
```

The authoritative route catalog is
[docs/api/api-reference.md](docs/api/api-reference.md). Trip CRUD,
collaboration, and itinerary mutations use Server Actions rather than internal
REST routes.

### Realtime Client (Supabase Realtime only - private channel)

```ts
import { createClient } from '@supabase/supabase-js'
const supabase = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!)
// authorize realtime with access token via RealtimeAuthProvider in app
const channel = supabase.channel(`user:${userId}`, { config: { private: true } })
channel.on('broadcast', { event: 'chat:message' }, ({ payload }) => console.log(payload))
channel.subscribe()
```

---

## Contributing

We welcome contributions! See the [Development Guide](docs/development/core/development-guide.md) for the full workflow, code standards, and testing details.

---

## Performance

TripSage AI is optimized for high performance and global scalability:

- **Response Times**: Sub-200ms for cached requests via Upstash Redis HTTP API
- **Edge Performance**: Sub-10ms global latency with Vercel Edge runtime and Upstash Redis distributed caching
- **Throughput**: 1000+ requests/second on standard hardware with Upstash serverless scaling
- **Vector Search**: Supabase pgvector with HNSW indexes for sub-50ms semantic similarity queries
- **Streaming**: Real-time SSE with AI SDK v6, interleaved tool calls, and progressive UI rendering
- **Background Processing**: Upstash QStash handles async jobs (memory sync, batch operations) with guaranteed delivery

### Benchmarks

```bash
# Performance testing via load testing tools
pnpm test --grep performance

# Or use external load testing
autocannon -c 100 -d 30 http://localhost:3000/api/health
```

---

## Security

Zero-trust architecture with defense-in-depth security:

- **BYOK Architecture**: User API keys encrypted in Supabase Vault, accessed only via SECURITY DEFINER RPCs with PostgREST JWT claims validation—keys never reach client
- **Row Level Security**: Supabase RLS policies enforce per-user data isolation; all tables protected by default
- **Rate Limiting**: Upstash Ratelimit with sliding-window counters, tiered budgets (40 req/min streaming, 20 req/min validation) per user/IP
- **Server-Only Secrets**: BYOK routes import `"server-only"` and run with `dynamic = "force-dynamic"` to ensure secrets processed per-request
- **PII Redaction**: OpenTelemetry spans automatically redact sensitive data; structured logging with correlation IDs
- **Tool Approval Gates**: Critical operations (bookings, payments) pause streaming and require explicit user consent
- **Dependency Security**: Dependabot provides automated vulnerability scanning in CI; `pnpm audit` is available for local/manual checks (not run in CI)

### Security Testing

```bash
# Security verification (ensure no hardcoded secrets)
git grep -i "fallback-secret\|development-only" .  # Should return empty

# Dependency audit
pnpm audit

# Run security-focused tests
pnpm test --grep security
```

---

### Runtime Validation

- **Provider validation**: `/api/keys/validate` verifies BYOK provider keys
  server-side without exposing secret material.
- **Operator health**: `/api/health/byok` uses `BYOK_HEALTHCHECK_KEY` and
  reports provider readiness without returning Vault values.
- **Deploy smoke**: `pnpm deploy:smoke -- --url "$DEPLOYMENT_URL"`
  checks health, security headers, auth guards, BYOK health when configured,
  and QStash-protected jobs before promotion.

---

## Monitoring & Observability

- **Health Checks**: Endpoint monitoring with health checks
- **Logging**: Structured logging with correlation IDs
- **Metrics**: Custom business metrics and performance tracking
- **Error Tracking**: Detailed error reporting and alerting

---

## License

This project is licensed under the MIT License - see the
[LICENSE](LICENSE) file for details.

---

> Built by **Bjorn Melin** as an exploration of AI-driven travel planning.
