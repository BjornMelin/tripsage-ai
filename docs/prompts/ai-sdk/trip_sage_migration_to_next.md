# TripSage AI Migration to Next.js 16 + Vercel AI SDK v6

## Overview and Goals

We are migrating TripSage AI from a Python/FastAPI backend to a unified Next.js 16 application powered by Vercel AI SDK v6. Objectives:

- Preserve feature parity (chat, RAG, multi‑tool agents, BYOK, profiles) while simplifying the stack.
- Favor maintained libraries and platform features over custom code (library‑first).
- Streamline operations: serverless runtime, global rate limiting, observability, multi‑provider routing.

This plan eliminates the separate FastAPI service. All backend logic runs in Next.js (App Router) using TypeScript.

## Final Decisions (2025‑11)

Weighted decision framework: Solution Leverage 35%, Application Value 30%, Maintenance Load 25%, Adaptability 10%. We finalize choices scoring ≥ 9.0/10.

- Default model routing: Vercel AI Gateway for non‑BYOK traffic; direct provider only for BYOK. (9.13/10)
- Runtime for chat routes: Edge Runtime (when all dependencies use HTTP/Fetch clients). (9.20/10)
- Orchestration: AI SDK Agents + tool calling with `streamText` and AI SDK UI Chatbot tool‑usage pattern (no bespoke orchestrator class). (9.40/10)
- Authentication: Supabase Auth + `@supabase/ssr`; Next.js 16 `proxy.ts` for session refresh, not `middleware.ts`. (9.05/10)
- RAG store: Supabase Postgres + pgvector (hybrid search preserved). (9.10/10)
- Rate limiting + cache: Upstash Redis (`@upstash/ratelimit`, `@upstash/redis`). (9.30/10)
- Observability: OpenTelemetry via `@vercel/otel` + Trace Drains. Minimal app logs; PII‑safe. (9.00/10)

## Architecture Overview

- Next.js 16 (App Router). Route Handlers and Server Components; Edge Runtime for streaming chat endpoints when possible.
- Vercel AI SDK v6 for LLMs, tools, structured outputs, UI streaming.
- Vercel AI Gateway for multi‑provider routing/telemetry; direct provider path for BYOK.
- Supabase: Auth, Postgres, pgvector, RLS. `@supabase/ssr` for SSR clients.
- Upstash Redis: rate limiting and short‑TTL caching over REST.
- Observability: `@vercel/otel` traces; Trace Drains to external systems.

Key references:

- AI SDK 6 Beta: <https://ai-sdk.dev/docs/announcing-ai-sdk-6-beta>
- Agents Overview: <https://ai-sdk.dev/docs/agents/overview>
- Tool Calling: <https://ai-sdk.dev/docs/ai-sdk-core/tools-and-tool-calling>
- Chatbot Tool Usage: <https://ai-sdk.dev/docs/ai-sdk-ui/chatbot-tool-usage>
- Next.js 16 blog (Proxy): <https://nextjs.org/blog/next-16#proxyts-formerly-middlewarets>
- Supabase SSR (Next.js): <https://supabase.com/docs/guides/auth/server-side/nextjs>
- Upstash Ratelimit template: <https://vercel.com/templates/next.js/ratelimit-with-upstash-redis>
- Vercel OTel + Drains: <https://vercel.com/docs/otel> , <https://vercel.com/docs/drains/reference/traces>

## Feature Migration Details

### 1) Agent Orchestration and Tools

Use AI SDK v6 Agents and the documented loop pattern. Implement tools with `tool()` and orchestrate with `streamText` including the `tools` set and `toolChoice: 'auto'` when desired. The model proposes tool invocations; server executes; outputs are fed back as part of the loop until completion.

- Tools: Define with Zod `inputSchema` and an async `execute` function.
- Approval: For sensitive tools, use the AI SDK UI Chatbot tool‑usage pattern to request user confirmation before executing. Property names for tool approval are UNVERIFIED—follow the documented UI approval flow in Chatbot Tool Usage.
- Structured outputs: Where appropriate, return objects via AI SDK v6 structured output facilities and validate client consumption accordingly.

Notes:

- Reranker support is provider‑dependent (UNVERIFIED in general v6 docs); integrate via the relevant provider’s rerank API when needed.

### 2) Chat UI and Streaming

- Use `@ai-sdk/react` `useChat` with the AI SDK UI Chatbot components.
- In Route Handlers, call `streamText({ model, messages, tools, toolChoice })` and return a streaming response.
- Enable resume support where needed (UI Resume Streams) and message persistence as applicable.

### 3) Retrieval‑Augmented Generation (RAG)

- Storage: Supabase Postgres with pgvector.
- Indexing: Use provider embeddings to upsert document chunks into `embeddings` table.
- Query: Hybrid search (vector + keywords as needed). Consider a reranker (provider‑dependent, UNVERIFIED) to refine top‑k before final prompt assembly.
- Caching: Cache frequent queries briefly in Upstash when end‑to‑end latency is dominated by external calls.

### 4) Multi‑Provider Models and BYOK

- Default path: Vercel AI Gateway for non‑BYOK traffic. Configure models by slug and manage budgets/routing in the dashboard.
- BYOK: If a user supplies their own provider key, create a direct provider instance with that key server‑side and bypass the gateway for that user’s calls. Store keys in Supabase under RLS; never expose to the client.

### 5) Authentication, Authorization, and Profiles

- Use `@supabase/ssr` to create:
  - Browser client (`createBrowserClient`) for Client Components.
  - Server client (`createServerClient`) for Server Components, Route Handlers, and Server Actions.
- Next.js 16 network boundary: add `proxy.ts` at the project root (or `src/proxy.ts`) — not under `app/` — to handle session refresh on incoming requests, per Next 16 guidance.
- Enforce Row‑Level Security (RLS) policies so users only access their data.
- Profile pages: prefer Supabase UI building blocks or shadcn/ui to minimize custom forms.

### 6) Rate Limiting, Caching, and Reliability

- Upstash Ratelimit (`@upstash/ratelimit`) with REST Redis (`@upstash/redis`).
- Identifier: use `user.id` (authenticated) or `req.ip` fallback.
- Apply per‑route limits (e.g., sliding window) and return 429 with minimal payload on overflow.
- Cache expensive results (short TTL) to absorb bursts; avoid caching small/cheap calls that don’t amortize the extra network hop.

### 7) Observability and Telemetry

- Initialize OpenTelemetry via `@vercel/otel` (`instrumentation.ts`).
- Configure Vercel Trace Drains to export traces to your observability backend.
- Log structured events for key actions (tool executed, model error). Redact PII and secrets. Prefer traces + minimal logs over verbose logging.

## Implementation Plan (Final)

1) Foundations
   - Install AI SDK v6 packages (`ai`, `@ai-sdk/react`, provider packages), Supabase (`@supabase/ssr`, `@supabase/supabase-js`), and Upstash (`@upstash/ratelimit`, `@upstash/redis`).
   - Configure Vercel AI Gateway for default model routing; set env vars.
   - Add `instrumentation.ts` for OTel.
2) Auth & Session
   - Implement `createBrowserClient` and `createServerClient` helpers.
   - Add `proxy.ts` at the project root (or `src/proxy.ts`) to refresh Supabase sessions at the network boundary (Next 16).
3) Chat API + UI
   - Implement a streaming Route Handler using `streamText` with tools.
   - Wire `useChat` + AI SDK UI Chatbot components; enable tool usage and approvals.
4) Tools & Integrations
   - Port Python integrations to AI SDK tools with Zod schemas, robust error handling, and concise outputs.
   - Add sensitive‑action approval flow via UI tool usage pattern.
5) RAG
   - Migrate/verify embeddings schema in Supabase; implement indexer and retriever.
   - Optionally integrate provider reranker (UNVERIFIED) behind a clean interface.
6) Rate limiting & Cache
   - Add Upstash Ratelimit per route; short‑TTL caching where it demonstrably helps.
7) Observability
   - Verify OTel traces appear; configure Trace Drains to your backend; ensure PII controls.

## Testing and Quality Gates

- Unit/integration tests for Route Handlers (chat, tools), RAG retriever, and rate limits.
- SSR auth tests for `createServerClient` flows.
- Lint/format/type: ruff/biome (repo standard), TypeScript strict, CI gates per project guidelines.

## Notes and Caveats

- Tool approval property names are UNVERIFIED; follow the Chatbot Tool Usage docs for user confirmation flows.
- Rerankers are provider dependent and may require specific provider SDKs or Gateway configuration.
- Ensure all dependencies used on Edge are fetch/HTTP‑based; if you require Node‑only clients, keep those endpoints on the Node runtime.
