# SPEC-0028: TripSage Agent Router & Workflow HTTP API - Functional & Technical Spec

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-11-21
**Category**: Frontend
**Domain**: AI Orchestration
**Related ADRs**: [ADR-0051](../../architecture/decisions/adr-0051-agent-router-workflows.md)
**Related Specs**:

## 1. Summary

This spec defines the TripSage Agent Router & Workflow HTTP API. It covers:

- A classification endpoint (`/api/agents/router`) that maps user messages to
  workflows using AI SDK v6 structured outputs.
- Per-workflow endpoints under `/api/agents/*` that execute dedicated AI agents
  (destination research, flights, accommodations, itineraries, budget,
  memory).
- Shared guardrails for auth, rate limiting, telemetry, and validation.

**The design aligns with:**

- Next.js 16 App Router and Server Components:
  - <https://nextjs.org/docs/app>
- AI SDK v6:
  - <https://ai-sdk.dev/docs/introduction>
- Supabase SSR:
  - <https://supabase.com/docs/guides/auth/server-side>
- Upstash Redis & Ratelimit:
  - <https://upstash.com/docs/redis/howto/connectwithupstashredis>
  - <https://upstash.com/docs/redis/sdks/ratelimit-ts/gettingstarted>
- Zod v4:
  - <https://zod.dev/v4>
- Vercel OTEL:
  - <https://vercel.com/docs/observability/otel-overview>

## 2. Goals

- Provide a consistent HTTP interface for all TripSage agent workflows.
- Centralize validation using Zod v4 schemas in `@schemas/agents`.
- Enforce auth, rate limiting, and telemetry via `withApiGuards`.
- Use AI SDK v6 streaming primitives for all workflow execution routes.
- Make it easy to add new workflows without reworking clients.

## 3. Non-Goals

- Building a general-purpose multi-tenant orchestration platform.
- Modeling long-running background workflows or QStash-based jobs (this spec
  is HTTP-only; QStash usage is covered elsewhere).
- Replacing the existing `/api/chat/stream` route; instead, the chat layer may
  delegate to these agent endpoints.

## 4. User Stories

- As a TripSage user, I want the system to interpret my free-form prompts and
  route them to the most relevant specialist agent so I get focused, high-
  quality answers.
- As a TripSage user, I want flight, hotel, and itinerary recommendations with
  streaming updates and clear explanations.
- As a TripSage user, I want TripSage to remember and reuse my preferences
  (memory workflow) across sessions.
- As a developer, I want a single source of truth for agent schemas and HTTP
  endpoints so I can extend the platform safely and predictably.

## 5. User Flows

### 5.1 Router classification

1. Frontend sends the latest user message and context to `POST /api/agents/router`.
2. Server validates input with `agentSchemas.routerRequestSchema`.
3. Server calls `classifyUserMessage` which uses AI SDK v6 `generateObject`
   with `routerClassificationSchema`.
4. Server returns a JSON classification:
   - `agent` (`AgentWorkflowKind`)
   - `confidence` (0–1)
   - optional `reasoning`.
5. Client decides to:
   - Call the corresponding workflow endpoint; or
   - Fall back to a general chat route if confidence is low.

### 5.2 Workflow execution (example: destination research)

1. Client calls `POST /api/agents/destinations` with a body conforming to
   `DestinationResearchRequest`.
2. `withApiGuards`:
   - Validates auth using Supabase SSR.
   - Applies `agents:destinations` rate limit via Upstash.
   - Initializes telemetry span.
3. Route handler parses body using `agentSchemas.destinationResearchRequestSchema`.
4. Route handler resolves provider with `resolveProvider`.
5. Route handler calls `runDestinationAgent`, which:
   - Builds a system prompt.
   - Calls AI SDK v6 `streamText` with tools and/or schemas.
   - Produces a `UIMessageStream` via `result.toUIMessageStreamResponse`.
6. Response streams back to client; UI renders updates incrementally.

The same pattern applies to flights, accommodations, itineraries, budget, and
memory workflows, using their respective schemas and agent functions.

### 5.3 Error and edge states

- Invalid JSON → 400 with structured error payload.
- Zod validation failure → 400 with `issues`.
- Auth failure → 401/403 from `withApiGuards`.
- Rate limit exceeded → 429 with headers from Upstash Ratelimit.
- AI provider error → 5xx with OTEL trace and redacted error message.

## 6. Data Model & Schemas

Canonical location: `frontend/src/domain/schemas/agents.ts`.

Key schema groups (Zod v4):

- **Core enums and types**
  - `AgentWorkflowKind` – enum for routing-level workflow IDs.
  - `AgentSource` – standardized citation object with `url`, `title`, etc.
- **Workflow-specific request/response schemas**
  - `destinationResearchRequestSchema`, `destinationResearchResultSchema`.
  - `flightSearchRequestSchema`, `flightSearchResultSchema`.
  - `accommodationSearchRequestSchema`, `accommodationSearchResultSchema`.
  - `itineraryPlanRequestSchema`, `itineraryPlanResultSchema`.
  - `budgetPlanRequestSchema`, `budgetPlanResultSchema`.
  - `memoryUpdateRequestSchema`, `memoryUpdateResultSchema`.
- **Router schemas**
  - `routerRequestSchema` – classification input.
  - `routerClassificationSchema` – classification output for AI SDK v6
    `generateObject`.
- **Monitoring & workflows (for dashboards and future tooling)**
  - `Agent`, `AgentActivity`, `ResourceUsage`, `AgentSession`.
  - `AgentWorkflowEntity`, `WorkflowConnection`.

Schema requirements:

- All schemas must be `.strict()` or equivalent via strongly typed fields.
- No `any` types; ambiguous data uses `unknown` + narrowings.
- Validation error messages should use `error:` options, not custom error maps.

## 7. API Design & Integration Points

All endpoints live under `frontend/src/app/api/agents/**/route.ts` and import
`"server-only"`.

### 7.1 Router endpoint

- Method: `POST`
- Path: `/api/agents/router`
- Request body: `RouterRequest` (from `agentSchemas.routerRequestSchema`).
- Response: JSON `RouterClassification`.
- Behavior:
  - Validates request via Zod.
  - Uses `resolveProvider` and AI SDK v6 `generateObject`.
  - Returns classification result.

### 7.2 Workflow endpoints

Common patterns:

- `withApiGuards({ auth: true, rateLimit: "<namespace>", telemetry: "<name>" })`
- Parse body via workflow-specific Zod request schema.
- Use `resolveProvider` to obtain a `LanguageModel`.
- Call workflow function (`runDestinationAgent`, `runFlightAgent`, etc.).
- Return `result.toUIMessageStreamResponse({ onError })`.

Endpoints:

- `POST /api/agents/destinations`
  - Request: `DestinationResearchRequest`
  - Telemetry: `agent.destinationResearch`
  - Rate limit key: `agents:destinations`
- `POST /api/agents/flights`
  - Request: `FlightSearchRequest`
  - Telemetry: `agent.flightSearch`
  - Rate limit key: `agents:flight`
- `POST /api/agents/accommodations`
  - Request: `AccommodationSearchRequest`
  - Telemetry: `agent.accommodationSearch`
  - Rate limit key: `agents:accommodations`
- `POST /api/agents/itineraries`
  - Request: `ItineraryPlanRequest`
  - Telemetry: `agent.itineraryPlanning`
  - Rate limit key: `agents:itineraries`
- `POST /api/agents/budget`
  - Request: `BudgetPlanRequest`
  - Telemetry: `agent.budgetPlanning`
  - Rate limit key: `agents:budget`
- `POST /api/agents/memory`
  - Request: `MemoryUpdateRequest`
  - Telemetry: `agent.memoryUpdate`
  - Rate limit key: `agents:memory`

### 7.3 Supporting services

- **Supabase SSR**
  - `createServerSupabase` in `frontend/src/lib/supabase/server.ts` must use
    `@supabase/ssr` as per:
    - <https://supabase.com/docs/guides/auth/server-side>
- **Upstash Redis & Ratelimit**
  - Redis client created via `Redis.fromEnv()`:
    - <https://upstash.com/docs/redis/howto/connectwithupstashredis>
  - Ratelimit via `@upstash/ratelimit`:
    - <https://upstash.com/docs/redis/sdks/ratelimit-ts/gettingstarted>
- **Telemetry**
  - Route handlers must be traceable via `@vercel/otel`:
    - <https://vercel.com/docs/observability/otel-overview>

## 8. UI / UX States

Each workflow and the router must handle:

- **Loading**
  - Spinner/skeleton while waiting for first streamed tokens.
- **Success (streaming)**
  - Incremental rendering of agent responses.
  - Optional citation badges using `AgentSource` URLs.
- **Empty**
  - No results state where agent returns minimal content.
- **Error**
  - User-friendly error banner/toast with retry options.
  - Telemetry event includes simplified error code and workflow ID.
- **Unauthorized**
  - Prompt to log in or reauthenticate.
- **Rate limited (429)**
  - UX message indicating the user has hit a usage cap; show retry after.

Chat surfaces using `useChat` transport should:

- Inspect router metadata (e.g., `agent` and `request`) and call the
  appropriate `/api/agents/*` endpoint.
- Fall back to `/api/chat/stream` when no agent is selected or confidence is
  too low.

## 9. Observability & Telemetry

Requirements:

- All `/api/agents/*` handlers must be wrapped in OTEL spans with:
  - Workflow name (`agent.workflow`).
  - Model and provider info (redacted where necessary).
  - Rate limit outcomes (allowed/blocked).
- Errors must capture stack traces where available (server-only).
- Logs:
  - Use OTEL exporters; `console.log` and `console.error` are disallowed in
    these files.

References:

- Vercel OTEL:
  - <https://vercel.com/docs/observability/otel-overview>
  - <https://vercel.com/docs/tracing/instrumentation>
- OpenTelemetry:
  - <https://opentelemetry.io/docs/>

## 10. Testing Strategy

Frameworks and tools:

- Vitest: <https://vitest.dev/guide/>
- React Testing Library:  
  <https://testing-library.com/docs/react-testing-library/intro/>
- MSW (Mock Service Worker): <https://mswjs.io/docs/>

Testing requirements:

- **Route handler tests (Node env)**
  - Use Vitest with `/** @vitest-environment node */` where needed.
  - Mock:
    - `next/headers` (`cookies`, `headers`).
    - `@/lib/supabase/server` (`createServerSupabase`, `getCurrentUser`).
    - `@/lib/redis` and Upstash rate limiters.
    - `@ai/models/registry` (`resolveProvider`) to supply deterministic models.
  - Cover:
    - Happy path.
    - Validation errors.
    - Auth failures.
    - Rate limit exceeded.
    - Provider failures.

- **Client and integration tests (jsdom env)**
  - Use `/** @vitest-environment jsdom */` for tests using DOM or React.
  - Use React Testing Library for UI states (loading, success, error).
  - Use MSW to mock `/api/agents/*` and `/api/agents/router`.

- **Coverage**
  - Target ≥ 90% coverage on:
    - `frontend/src/app/api/agents/**/route.ts`
    - `frontend/src/lib/agents/**`
    - `frontend/src/domain/schemas/agents.ts` (via validation tests).

## 11. Risks & Open Questions

- **Classification accuracy**
  - Risk: Misrouted messages degrade UX.
  - Mitigation: Use confidence thresholds, reasoning, and fallback flows.

- **Rate limit tuning**
  - Risk: Overly strict limits cause frustration; too loose limits increase
    costs.
  - Mitigation: Start conservative, capture metrics, and tune.

- **Model/provider surface**
  - Some workflows may require specific models (e.g., structured tools vs pure
    text). The provider registry must encode these constraints.

- **Future expansion**
  - Additional workflows (e.g., loyalty programs, calendar sync) may need
    additional endpoints and schema evolution.
