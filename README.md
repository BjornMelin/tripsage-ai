# 🌟 TripSage AI

[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org)
[![AI SDK v6](https://img.shields.io/badge/Vercel%20AI%20SDK-v6-blue.svg)](https://v6.ai-sdk.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.4+-blue.svg)](https://typescriptlang.org)
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

- **Multi-Provider AI Routing**: Vercel AI Gateway with automatic fallback across OpenAI, Anthropic, xAI, and OpenRouter—BYOK support with encrypted key storage
- **Agentic Tool Orchestration**: 15+ production-ready tools via AI SDK v6 with Zod validation—flights (Duffel), accommodations (MCP), weather, maps, planning, and memory
- **Hybrid RAG Pipeline**: Vector similarity search with Supabase pgvector + keyword fusion, Cohere Rerank v3.5 for optimal retrieval accuracy
- **Structured Outputs**: Schema-first LLM responses with `generateObject` for deterministic parsing and type-safe validation
- **Streaming Intelligence**: Real-time SSE streaming with interleaved tool calls and generative UI components

### Data & Infrastructure

- **Supabase PostgreSQL + pgvector**: Managed database with HNSW indexes for semantic search, embeddings storage, and vector similarity queries
- **Supabase Auth & Vault**: Server-side authentication with SSR clients (`@supabase/ssr`), encrypted BYOK secrets in Vault with RLS-gated access
- **Supabase Realtime**: Private channels with Row Level Security for multi-user collaboration, presence tracking, and broadcast events
- **Supabase Storage**: File uploads with signed URL access, metadata persistence, and server-enforced access control

### Performance & Scalability

- **Upstash Redis**: Serverless HTTP Redis for sub-10ms global caching, sliding-window rate limiting, and deduplication keys
- **Upstash QStash**: Webhook-driven background jobs with signature verification, Redis idempotency gates, and batch processing (memory sync, async tasks)
- **Edge-First Architecture**: Next.js 16 Edge runtime support, Vercel deployment with global CDN, optimized for low-latency responses
- **React Compiler**: Automatic memoization and zero-overhead reactive rendering for optimal performance

### Security & Compliance

- **Zero-Trust Architecture**: BYOK keys never touch client; server-only routes with `"server-only"` imports and dynamic execution
- **Row Level Security**: Supabase RLS policies enforce per-user data isolation; security-definer RPCs guard Vault access
- **Rate Limiting**: Upstash Ratelimit with tiered budgets (40 req/min streaming, 20 req/min validation) per user/IP
- **OpenTelemetry**: Distributed tracing with PII redaction, span instrumentation, and Trace Drains for observability without data leakage
- **Tool Approval Flows**: Sensitive operations (bookings, payments) pause streaming and require explicit user consent

### Modern Frontend

- **Next.js 16 + React 19**: App Router with RSC-first architecture, Server Components by default, React Compiler enabled
- **TypeScript 5.9**: Strict mode with end-to-end type safety, Zod schemas as single source of truth
- **AI SDK v6 Native**: Complete TypeScript migration from Python—unified provider API, native streaming, edge runtime support

## Quick Start

### Prerequisites

- **Node.js 24+** with pnpm 10.20.0
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
- **AI Routing**: Vercel AI Gateway for multi-provider orchestration with automatic fallback, BYOK support via Supabase Vault
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
pnpm biome:check
pnpm test:run       # Vitest
pnpm test:e2e       # Playwright

# Supabase tooling (optional)
make supa.link PROJECT_REF=...
make supa.db.push
```

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

- Server-first: Route handlers and Server Actions own data fetching and AI calls. Use `createAI`/`streamText` with Zod v4 validation.
- Auth/DB: `@supabase/ssr` only; no auth-helpers.
- Cache/jobs: Upstash HTTP clients only (`Redis.fromEnv`, QStash SDK).
- Logging: OTEL exporters; no `console.log` in server code.
- Tests: Vitest/Playwright only (no pytest/ruff/uv).

---

## Deployment

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Production build
docker build -t tripsage-ai .
docker run -p 3000:3000 --env-file .env.production tripsage-ai
```

### Kubernetes Deployment

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -l app=tripsage-ai
```

### Environment Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL | ✅ |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anonymous key | ✅ |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key | ✅ |
| `AI_GATEWAY_API_KEY` | Vercel AI Gateway key | ✅ |
| `DUFFEL_ACCESS_TOKEN` | Duffel API token for flights | ⚠️ |
| `UPSTASH_REDIS_REST_URL` | Upstash Redis REST URL | ⚠️ |
| `UPSTASH_REDIS_REST_TOKEN` | Upstash Redis REST token | ⚠️ |

✅ Required | ⚠️ Optional (fallback available)

**Notes:**

- All routes use Upstash REST credentials for rate limiting and caching via `@upstash/redis` and `@upstash/ratelimit`.
- BYOK keys are stored encrypted in Supabase Vault and resolved server-side only.

---

## 🔌 API Overview

### Core Endpoints

```bash
# Authentication
POST /api/auth/login              # User login
POST /api/auth/register           # User registration
POST /api/auth/refresh            # Token refresh

# Trip Management
GET  /api/trips                   # List user trips
POST /api/trips                   # Create new trip
GET  /api/trips/{id}              # Get trip details
PUT  /api/trips/{id}              # Update trip
DELETE /api/trips/{id}            # Delete trip

# Flight Services
GET  /api/flights/search          # Search flights
POST /api/flights/book            # Book selected flight
GET  /api/flights/bookings        # List user bookings

# AI Chat & Memory
POST /api/chat/completions        # AI chat interface
POST /api/memory/conversation     # Store conversation
GET  /api/memory/context          # Get user context
```

### Realtime Client (Supabase Realtime only - private channel)

```ts
import { createClient } from '@supabase/supabase-js'
const supabase = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!)
// authorize realtime with access token via RealtimeAuthProvider in app
const channel = supabase.channel(`user:${userId}`, { config: { private: true } })
channel.on('broadcast', { event: 'chat:message' }, ({ payload }) => console.log(payload))
channel.subscribe()
```

---

## 🤝 Contributing

We welcome contributions! See the [Development Guide](docs/development/development-guide.md) for the full workflow, code standards, and testing details.

---

## 📈 Performance

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
pnpm test:run --grep performance

# Or use external load testing
autocannon -c 100 -d 30 http://localhost:3000/api/health
```

---

## 🔒 Security

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
pnpm test:run --grep security
```

---

### Service Validation

- **Unified result model**: Both API key validation and external service health checks return an `ApiValidationResult`, eliminating duplicate response types.
- **Context-aware fields**: Validation flows populate `is_valid`, `status`, and `validated_at`, while health probes use `health_status`, `checked_at`, and leave validation-only fields unset (`None`).
- **Shared metadata**: Rate-limit quotas, capability discovery, latency timing, and diagnostic details flow through identical fields for streamlined analytics and caching.
- **Computed insights**: `success_rate_category` and `is_healthy` computed fields provide quick rollups regardless of whether the result originated from validation or monitoring.

---

## 📊 Monitoring & Observability

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
