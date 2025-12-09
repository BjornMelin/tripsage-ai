# ADR-0051: TripSage Agent Router and Workflow HTTP API

Status: Accepted  
Date: 2025-11-21
Category: Architecture
Domain: AI Orchestration / Frontend
Related ADRs: ADR-0031, ADR-0036, ADR-0038, ADR-0042
Related Specs: SPEC-0028

## Context

TripSage is migrating to a 2025 architecture based on:

- Next.js 16 App Router and Server Components:
  - <https://nextjs.org/docs>
  - <https://nextjs.org/docs/app>
  - Caching and cache components:
    - <https://nextjs.org/docs/app/guides/caching>
    - <https://nextjs.org/docs/app/getting-started/cache-components>
- Vercel AI SDK v6 for AI workflows, streaming, and tool calling:
  - Docs: <https://ai-sdk.dev/docs/introduction>
  - v6 announcement: <https://ai-sdk.dev/docs/announcing-ai-sdk-6-beta>
  - Vercel docs entry: <https://vercel.com/docs/ai-sdk>
- Supabase JS + SSR auth:
  - SSR overview: <https://supabase.com/docs/guides/auth/server-side>
  - `@supabase/ssr` client creation: <https://supabase.com/docs/guides/auth/server-side/creating-a-client>
  - Migration from auth helpers: <https://supabase.com/docs/guides/auth/server-side/migrating-to-ssr-from-auth-helpers>
- Upstash Redis and Ratelimit:
  - HTTP client: <https://upstash.com/docs/redis/howto/connectwithupstashredis>
  - TS Ratelimit SDK: <https://upstash.com/docs/redis/sdks/ratelimit-ts/gettingstarted>
  - Deployment and `Redis.fromEnv()`: <https://upstash.com/docs/redis/sdks/ts/deployment>
- Zod v4 schemas as single source of truth:
  - Intro: <https://zod.dev/>
  - v4 release notes: <https://zod.dev/v4>
- Observability via OpenTelemetry and Vercel OTEL:
  - OTEL overview: <https://opentelemetry.io/docs/>
  - Vercel OTEL overview: <https://vercel.com/docs/observability/otel-overview>
  - Instrumentation guide: <https://vercel.com/docs/tracing/instrumentation>

`AGENTS.md` defines global rules for AI-related code in this repo, including:

- Canonical use of AI SDK v6 in server-first patterns.
- Supabase SSR-only auth access in server contexts.
- Upstash rate limiting and caching as the default guardrail stack.
- Zod v4 as the only allowed validation layer for API contracts.

TripSage needs a consistent, HTTP-based agent router and workflow API that:

- Classifies user messages into workflow types (e.g., `destinationResearch`, `flightSearch`, `itineraryPlanning`, `accommodationSearch`, `budgetPlanning`, `memoryUpdate`).
- Exposes separate, guardrailed route handlers per workflow under `/api/agents/*`.
- Uses shared Zod schemas from `src/domain/schemas/agents.ts`.
- Applies centralized auth, rate limiting, and telemetry via `withApiGuards`.
- Streams AI responses using AI SDK v6 primitives in route handlers.

Historically, classification logic and per-agent flows risk drifting across components, client hooks, and route handlers. This ADR standardizes a single HTTP API shape and associated architecture.

## Decision

We will:

1. **Standardize agent workflows and types**

   - Use `AgentWorkflowKind` and associated Zod schemas from
     `src/domain/schemas/agents.ts` as the canonical source.
   - Supported workflows:
     - `destinationResearch`
     - `itineraryPlanning`
     - `flightSearch`
     - `accommodationSearch`
     - `budgetPlanning`
     - `memoryUpdate`
     - `router` (classification only)

2. **Introduce a dedicated router HTTP endpoint**

   - Route: `POST /api/agents/router` implemented in
     `src/app/api/agents/router/route.ts`.
   - Uses AI SDK v6 `generateObject` and a Zod schema (`routerClassificationSchema`)
     to classify the latest user message into one of the supported workflows with
     confidence and reasoning.
   - Uses `withApiGuards({ auth: true, rateLimit: "agents:router", telemetry: "agent.router" })`.
   - Uses `@supabase/ssr`-backed auth to resolve the current user where necessary.
   - Uses `resolveProvider` from `@ai/models/registry` to select the model provider
     (Vercel AI Gateway or BYOK) server-side.

3. **Expose one route per workflow with consistent guardrails**

   - Route handlers (all under `src/app/api/agents/**/route.ts`):
     - `POST /api/agents/destinations` → destination research agent
     - `POST /api/agents/flights` → flight agent
     - `POST /api/agents/accommodations` → accommodations agent
     - `POST /api/agents/itineraries` → itinerary agent
     - `POST /api/agents/budget` → budget agent
     - `POST /api/agents/memory` → memory agent
   - Each handler:
     - Imports `"server-only"`.
     - Uses `withApiGuards` with an `agents:*` route key and telemetry name
       (e.g., `agent.destinationResearch`, `agent.flightSearch`).
     - Parses input via the appropriate Zod schema from `agentSchemas`.
     - Resolves provider via `resolveProvider`.
     - Invokes a dedicated agent function (e.g., `runDestinationAgent`) that uses
       AI SDK v6 `streamText`/`streamObject` and returns
       `result.toUIMessageStreamResponse({ onError })`.

4. **Centralize rate limiting and reuse configuration**

   - Route-level limits stored in `src/lib/ratelimit/routes.ts` and
     accessed by `withApiGuards`:
     - `agents:router`: higher limit (classification-only).
     - `agents:*` workflows: more conservative limits.
   - Tool-level limits per workflow stored in
     `src/lib/ratelimit/config.ts` using `AgentWorkflowKind`.
   - Implementation uses Upstash Redis HTTP client:
     - <https://upstash.com/docs/redis/howto/connectwithupstashredis>
   - Ratelimit implementation uses `@upstash/ratelimit`:
     - <https://upstash.com/docs/redis/sdks/ratelimit-ts/gettingstarted>

5. **Align all schemas on Zod v4**

   - All agent-related request/response contracts live in
     `src/domain/schemas/agents.ts` using Zod v4.
   - Route handlers import from `@schemas/agents`.
   - Client components and stores (e.g., agent monitoring dashboards) reuse the
     same schemas for validation.

6. **Use OTEL-based telemetry and logging**

   - Telemetry for all `/api/agents/*` routes must be integrated with OTEL
     traces via `@vercel/otel`:
     - <https://vercel.com/docs/observability/otel-overview>
     - <https://vercel.com/docs/tracing/instrumentation>
   - No `console.log` or ad-hoc logging in route handlers; use OTEL spans and
     attributes for tracing agent runs, model IDs, and workflow outcomes.

## Options Considered

- **Option A – Keep agent logic embedded in chat routes and client hooks**
  - **Pros:**
    - Minimal refactor.
    - Fewer endpoints to manage.
  - **Cons:**
    - Harder to enforce consistent auth, rate limiting, and telemetry.
    - Client hooks risk coupling transport with agent orchestration.
    - Difficult to reuse workflows from non-chat surfaces (e.g., dashboards,
      batch jobs).

- **Option B – Implement a single monolithic `/api/agents` endpoint with a `type` field**
  - **Pros:**
    - Fewer HTTP endpoints.
    - Slightly simpler routing table.
  - **Cons:**
    - Complex, branching handler logic.
    - Rate limiting cannot be tuned per workflow.
    - Harder to enforce per-workflow telemetry and caching policies.

- **Option C – Dedicated router and per-workflow endpoints (chosen)**
  - **Pros:**
    - Clean separation of concerns: routing vs workflow execution.
    - Strong fit with `AgentWorkflowKind` and shared schemas.
    - Per-route rate limiting, telemetry, and PPR/caching.
    - Works well with AI SDK v6 patterns and AGENTS.md rules.
  - **Cons:**
    - More route files to maintain.
    - Requires coordinated changes in client `useChat` transport and monitoring
      components.

## Consequences

### Positive

- Clear, documented, and testable HTTP boundaries for all AI agents.
- Unified Zod v4 schemas across server and client.
- Shared guardrails (auth, rate limiting, telemetry) via `withApiGuards`.
- Extensible pattern for adding new workflows (e.g., `calendarPlanning`).
- Aligns with Next.js and AI SDK v6 best practices and AGENTS.md.

### Negative / Risks

- More routes and agent functions to keep in sync.
- Requires careful rate-limit tuning to avoid degrading UX.
- Classification errors in `/api/agents/router` can route messages to suboptimal
  workflows; mitigation via confidence thresholds and fallbacks is required.
- OTEL tracing adds complexity to configuration and local dev.

## References

- AGENTS contract: `AGENTS.md` at repo root.
- Next.js docs:
  - <https://nextjs.org/docs>
  - <https://nextjs.org/docs/app>
  - <https://nextjs.org/docs/app/guides/caching>
  - <https://nextjs.org/docs/app/getting-started/cache-components>
- AI SDK / Vercel AI:
  - <https://ai-sdk.dev/docs/introduction>
  - <https://ai-sdk.dev/docs/announcing-ai-sdk-6-beta>
  - <https://vercel.com/docs/ai-sdk>
- Supabase SSR:
  - <https://supabase.com/docs/guides/auth/server-side>
  - <https://supabase.com/docs/guides/auth/server-side/creating-a-client>
  - <https://supabase.com/docs/guides/auth/server-side/migrating-to-ssr-from-auth-helpers>
- Upstash Redis and Ratelimit:
  - <https://upstash.com/docs/redis/howto/connectwithupstashredis>
  - <https://upstash.com/docs/redis/sdks/ratelimit-ts/gettingstarted>
  - <https://upstash.com/docs/redis/sdks/ts/deployment>
- Zod:
  - <https://zod.dev/>
  - <https://zod.dev/v4>
- OpenTelemetry and Vercel OTEL:
  - <https://opentelemetry.io/docs/>
  - <https://vercel.com/docs/observability/otel-overview>
  - <https://vercel.com/docs/tracing/instrumentation>
- Testing (for future implementation work):
  - Vitest: <https://vitest.dev/guide/>
  - React Testing Library: <https://testing-library.com/docs/react-testing-library/intro/>
  - MSW: <https://mswjs.io/docs/>
