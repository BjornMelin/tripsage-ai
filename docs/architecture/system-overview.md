# System Architecture

Audience: technical contributors who need an up-to-date, implementation-focused picture of TripSage.

## Runtime Topology

```mermaid
graph TD
    FE["Next.js 16 (React 19)<br/>App Router · RSC-first · Client islands"] -->|"Route Handlers"| API["/api/*<br/>AI SDK v6 · Zod validation · BYOK/ Gateway"]
    API -->|"Auth + DB"| DB["Supabase PostgreSQL<br/>RLS · Vault · pgvector · Realtime"]
    API -->|"Cache / Limits"| REDIS["Upstash Redis<br/>HTTP API · sliding window"]
    API -->|"Background jobs"| QSTASH["Upstash QStash<br/>webhook tasks"]
    API -->|"Storage"| STORAGE["Supabase Storage<br/>signed URLs"]
    API -->|"Telemetry"| OTEL["OpenTelemetry via @vercel/otel"]
    API -->|"External providers"| PROVIDERS["Vercel AI Gateway / OpenAI / Anthropic / xAI<br/>Google Maps · Stripe · Resend · mem0"]
    FE --> RT["Supabase Realtime<br/>broadcast · presence"]
```

## Stack Snapshot (from `package.json`)

- Next.js `16.0.3`, React `19.2.x`, TypeScript `5.9.x`.
- AI SDK core `ai@6.0.0-beta.99`; React hooks `@ai-sdk/react@3.0.0-beta.99`; providers `@ai-sdk/openai`, `@ai-sdk/anthropic`, `@ai-sdk/xai`; gateway via `createGateway`.
- Supabase SSR `@supabase/ssr@0.7.0`, browser client `@supabase/supabase-js@2.80.0`, Vault, pgvector, Realtime.
- Upstash `@upstash/redis@1.35.6`, `@upstash/ratelimit@2.0.7`, `@upstash/qstash@2.8.4`.
- UI: Radix primitives, Tailwind CSS v4, shadcn/ui compositions, Framer Motion.
- Payments/Email: Stripe `^19.3.0`, Resend `^6.5.0`.
- Scheduling/Calendar: `ical-generator@10.0.0`, Google Calendar integration in `src/lib/calendar`.
- State: Server Components by default; client state with Zustand; server state with TanStack Query.
- Observability: `@vercel/otel`, `@opentelemetry/api` with helpers in `src/lib/telemetry` and `src/lib/logging`.
- Testing/tooling: Biome format/lint, Vitest, Playwright, `tsc`.

## Key Capabilities

- Streaming chat and tool calling via AI SDK v6 using shared Zod schemas in `src/schemas`.
- Agent routes for flights, accommodations, destinations, itineraries, budget, and memory (`/api/agents/*`) with domain-specific tool sets.
- BYOK + Vercel AI Gateway routing with explicit precedence: user gateway → user provider (OpenAI/Anthropic/xAI/OpenRouter) → team gateway fallback (opt-in).
- Memory pipeline backed by Supabase Postgres + pgvector; QStash jobs cap inserts to 50 messages per batch and enforce idempotency.
- Realtime collaboration (presence/broadcast) via Supabase Realtime; AI token streaming stays on AI SDK SSE.
- Attachments stored in Supabase Storage (`attachments` bucket) with Postgres metadata rows (owner, size, MIME, path) and signed URL access.
- Payments and notifications available through Stripe and Resend (keys remain server-side).

## Core Components

### Next.js Application

- App Router with RSC-first rendering; client components only where interactivity is required.
- Route handlers live in `src/app/api/**/route.ts`. They parse input (Zod), create request-scoped collaborators (Supabase, rate limiter, providers), and delegate to pure handlers. No module-scope state.
- AI SDK v6 is the only LLM transport (`streamText`, `generateObject`, `streamObject`); structured outputs use Zod schemas under `src/schemas`.
- Caching and rate limiting use per-request Upstash Redis/RateLimit instances. Auth-dependent routes remain dynamic (no cache).
- Background/async work uses QStash webhooks; handlers are stateless and idempotent.

### Identity and Security

- Supabase Auth with SSR cookie handling via `src/lib/supabase/server.ts` and middleware; browser client only for Realtime/subscriptions.
- Vault stores BYOK keys; provider resolution happens server-side through `src/ai/models/registry.ts`. BYOK routes import `"server-only"`.
- Randomness/timestamps come from `@/lib/security/random`; no `Math.random` or `crypto.randomUUID`.
- Key precedence (highest → lowest): user gateway key, user provider key (OpenAI/Anthropic/xAI/OpenRouter), team gateway key fallback (requires user consent flag).
- Auth-bound routes stay dynamic; do not add `'use cache'` or static revalidation to BYOK/user-scoped handlers.
  Routes accessing `cookies()` or `headers()` (required for Supabase SSR auth) cannot use cache directives per Next.js Cache Components restrictions.
  See [Spec: BYOK Routes and Security (Next.js + Supabase Vault)](../specs/archive/0011-spec-byok-routes-and-security.md).

### Data & Storage

- Single Supabase PostgreSQL with pgvector and JSONB for flexible metadata.
- Supabase Storage for uploads; access via signed URLs.
- Supabase Realtime for presence/broadcast; all channels created through `use-realtime-channel` and its thin wrappers (no direct `supabase.channel()` in new code).
- Storage buckets: primary bucket `attachments`; per-object metadata persisted in Postgres (size, MIME, path, owner) for auditability.

### Observability

- Use `withTelemetrySpan` / `withTelemetrySpanSync`, `recordTelemetryEvent`, and `createServerLogger` (see `src/lib/telemetry` and `src/lib/logging`). Console logging is reserved for tests/client-only code.
- OpenTelemetry exporters are wired through `@vercel/otel`; spans wrap API handlers and external calls.
- Critical-path failures should emit `emitOperationalAlert` for downstream alerting (see `src/lib/telemetry/alerts.ts`).

### External Integrations (present in repo)

- AI providers via Vercel AI Gateway or BYOK (OpenAI, Anthropic, xAI).
- Supabase platform services (Auth, Realtime, Storage, Vault, pgvector).
- Upstash Redis/Ratelimit for caching and throttling; Upstash QStash for jobs.
- Google Maps (types present), Stripe, Resend email, mem0 (memory SDK), Playwright for browser automation.

## Representative Workflows

- **Chat + tool calling**: `POST /api/chat/stream` → Zod validation → Supabase auth → Upstash rate limit → provider resolution → `streamText` with tools → SSE stream to UI → telemetry span with provider/tool attributes.
- **Flight or accommodation search**: `POST /api/agents/flights|accommodations` → same guard pipeline → domain tools (external API or MCP adapters) → structured results streamed back; attachments handled via signed URLs when present.
- **Memory sync job (QStash)**: Frontend enqueues job → QStash webhook calls `/api/jobs/memory-sync` with Upstash signature → signature verify + Redis idempotency key → payload validated → batch limited to 50 messages → Supabase inserts/updates chat session + memories → telemetry recorded; duplicates short-circuit with `{ duplicate: true }`.
- **Realtime collaboration**: Clients subscribe via `use-realtime-channel` to `session:{id}` / `trip:{id}` topics for presence/broadcast; server never emits LLM tokens over Realtime.
- **Attachments**: Client uploads to Supabase Storage (`attachments` bucket); server issues signed URLs; Postgres rows track ownership and metadata.
- **Notifications/Payments**: Stripe and Resend integrations are server-only; credentials resolved from env and never exposed to clients.

### Workflow visuals (Mermaid)

#### Chat streaming with tools

```mermaid
sequenceDiagram
    participant UI as Client UI (useChat)
    participant RH as Next.js Route Handler (/api/chat/stream)
    participant SUPA as Supabase (Auth/DB)
    participant RL as Upstash Ratelimit
    participant REG as Provider Registry
    participant LLM as AI SDK + Model
    participant OBS as Telemetry

    UI->>RH: POST messages+metadata
    RH->>SUPA: validate session (SSR client)
    RH->>RL: sliding window check
    RH->>REG: resolve provider (gateway/BYOK)
    RH->>LLM: streamText({ messages, tools, schema })
    LLM-->>RH: SSE deltas (text/tool calls)
    RH-->>UI: SSE stream (toUIMessageStreamResponse)
    RH->>OBS: span + attrs (provider, tool, latency)
```

#### QStash memory sync job

```mermaid
sequenceDiagram
    participant FE as Frontend (enqueue)
    participant QS as QStash
    participant RH as Next.js Job Handler (/api/jobs/memory-sync)
    participant SIG as Upstash Signature Verify
    participant REDIS as Upstash Redis (idempotency)
    participant DB as Supabase (chat_sessions, memories)
    participant OBS as Telemetry

    FE->>QS: Enqueue memory sync job (payload, idempotencyKey)
    QS-->>RH: POST webhook with signature
    RH->>SIG: verify(signature)
    SIG-->>RH: ok|fail
    RH->>REDIS: tryReserveKey(idempotencyKey)
    alt duplicate
        RH-->>QS: 200 { duplicate: true }
    else new
        note over RH: Zod validate payload, cap messages <= 50
        RH->>DB: upsert chat session rows
        RH->>DB: insert memories (pgvector)
        RH-->>QS: 200 { ok: true, memoriesStored }
    end
    RH->>OBS: span + counts + duplicate flag
```

## End-to-End Request Flow

1. Request enters `/api/*` route handler.
2. Supabase SSR client is created; session validated.
3. Guards: rate limiting and Zod input validation.
4. Provider resolution via registry (Gateway/BYOK).
5. Execution: AI SDK call and domain logic; optional QStash enqueue.
6. Persistence: Supabase read/write; Redis cache when applicable.
7. Response: SSE stream for chat routes or JSON for synchronous calls; telemetry spans emitted.

- Typical rate-limit profile (tuned per endpoint): streaming routes ~40 req/min sliding window; non-streaming ~20 req/min; keyed by user or IP.
- QStash handlers validate signatures and include idempotency keys to avoid duplicate side effects.

## Realtime Responsibilities

- Supabase Realtime handles multi-client fanout (chat events, presence, agent status). All subscriptions go through `use-realtime-channel` or thin wrappers; no direct `supabase.channel()` creation in new code.
- AI token streaming uses AI SDK SSE transports only; Realtime is never used for LLM token delivery.

## Deployment & Environments

- Local: `pnpm dev` for Next.js; Supabase CLI for local DB; Redis/QStash via Upstash cloud or mocks.
- Production: Vercel for frontend + API routes; Supabase managed Postgres/Storage/Realtime; Upstash Redis/QStash for cache/limits/jobs; AI Gateway for provider routing.
- Quality gates on touched code: `pnpm biome:check`, `pnpm type-check`, and relevant `pnpm test*`.

## Invariants

- Single Next.js codebase; legacy Python/FastAPI services are removed and unsupported.
- No custom streaming frameworks—AI SDK v6 is the sole LLM transport.
- Remove deprecated paths when new implementations land (final-only policy).
