# Spec 0026: Supabase Memory Orchestrator & Provider Adapters

**Version**: 1.0.0  
**Status**: Accepted  
**Date**: 2025-11-18

## Status

- Implementation complete. Orchestrator module (`lib/memory/orchestrator.ts`) is fully implemented with Supabase, Upstash, and Mem0 adapters.
- Integrated into chat stream handler (`api/chat/stream/_handler.ts`) via `persistMemoryTurn()`.
- All adapters support required intents: `onTurnCommitted`, `syncSession`, `backfillSession`, `fetchContext`.

## Goals

- Establish a canonical `memories` schema in Supabase Postgres with pgvector
  columns, Row Level Security, and automated embeddings pipelines.
- Introduce a Memory Orchestrator service (TypeScript module) that receives
  intents (`onTurnCommitted`, `syncSession`, `backfillSession`, `fetchContext`)
  and fans out to pluggable adapters.
- Provide first-party adapters: `SupabaseAdapter` (authoritative storage),
  `UpstashAdapter` (queues/caches), `Mem0Adapter` (optional enrichment).
- Ensure AI SDK v6 chat flows, Query Clients, and hooks interact with memory via
  orchestrator only—no direct provider calls from UI stores.
- Deliver actionable telemetry, retry, and PII redaction pipelines.

## Non-Goals

- Replacing existing client-side persistence (Zustand + storage) immediately.
- Introducing new backend runtimes; all logic stays within Next.js Route
  Handlers or shared libraries.
- Managing bespoke embedding models; we rely on OpenAI/Supabase-hosted models.

## Architecture Overview

```mermaid
flowchart TD
    A["Chat Store"] -->|intents| B["Memory Orchestrator (TS)"]
    B --> C["Supabase"]
    B --> D["Upstash"]
    B --> E["Mem0"]

    C --> F["canonical store"]
    D --> G["queues"]
    E --> H["retrieval"]
```

- **Orchestrator module** (`frontend/src/lib/memory/orchestrator.ts`)
  - Validates intents, enforces feature flags, runs PII redaction helpers, and
    emits OTLP spans/metrics.
  - Dispatches intents to adapters sequentially (Supabase → Upstash → Mem0 by
    default) with per-adapter error handling and exponential backoff metadata.

- **Adapters**
  - `SupabaseAdapter`: inserts/updates rows via `@supabase/postgrest-js`
    service role, manages embeddings with Supabase Edge Functions, and syncs
    last-write timestamps.
  - `UpstashAdapter`: publishes messages to QStash (`memory.sync` topic) and
    writes ephemeral caches to Redis (`memory:{user}:{session}`). Supports TTL
    invalidation and multi-region fanout.
  - `Mem0Adapter`: wraps `createMem0()` to push curated turns, enabling AI SDK
    `streamText` to retrieve previously stored facts.

## Data Model

- `memories.sessions`
  - `id (uuid PK)`, `user_id`, `title`, `last_synced_at`, `metadata jsonb`.
- `memories.turns`
  - `id (uuid PK)`, `session_id`, `role`, `content jsonb`, `attachments jsonb`,
    `tool_calls jsonb`, `tool_results jsonb`, `created_at`, `pii_scrubbed boolean`.
- `memories.turn_embeddings`
  - `turn_id`, `embedding vector`, `model`, `created_at`.

## API Contracts

```ts
type MemoryIntent =
  | { type: "onTurnCommitted"; sessionId: string; userId: string; turn: Message }
  | { type: "syncSession"; sessionId: string; userId: string }
  | { type: "backfillSession"; sessionId: string; userId: string }
  | { type: "fetchContext"; sessionId: string; userId: string; limit?: number };

interface MemoryAdapter {
  supportedIntents: MemoryIntent["type"][];
  handle(intent: MemoryIntent, ctx: MemoryContext): Promise<MemoryResult>;
}
```

## Security & Compliance

- Supabase schema secured via RLS: `user_id = auth.uid()` for user-facing
  reads; service role functions for background jobs.
- PII redaction service strips emails, phone numbers, payment card patterns
  prior to non-Supabase adapters. Hashes stored in metadata for auditing.
- Secrets: Mem0 + Upstash keys remain server-side; orchestrator obtains them via
  existing provider registry (ADR-0028).

## Observability & Retry

- OTLP spans: `memory.intent`, `adapter.supabase`, `adapter.upstash`,
  `adapter.mem0` with status + duration.
- Upstash QStash retry policy: exponential backoff, DLQ queue `memory.dlq`.
- Supabase Edge Functions log to central observability stack.

## Testing Strategy

- Unit tests for orchestrator + adapters (Vitest, mocked providers).
- Integration tests using Supabase test instance + Upstash HTTP mocks + Mem0
  test keys (or stub adapter).
- Playwright scenario verifying conversation memory recall round-trip.

## Rollout Plan

1. Ship orchestrator behind `memory.orchestrator` flag; chat store emits intents
   while still calling legacy memory to guarantee coverage.
2. Enable Supabase adapter, validate telemetry; disable legacy store calls.
3. Roll out Upstash + Mem0 adapters sequentially; monitor queue depth, provider
   quotas, and retrieval accuracy.
4. Remove feature flag once metrics stable (<0.1% failed syncs, <250 ms median
   orchestrator latency).

## References

- ADR-0042: Supabase-Centric Memory Orchestrator.  
- Supabase Vector documentation – <https://supabase.com/modules/vector?utm_source=openai>  
- Upstash AI SDK article – <https://upstash.com/blog/vercel-ai-sdk?utm_source=openai>  
- Mem0 Vercel AI SDK integration – <https://docs.mem0.ai/integrations/vercel-ai-sdk?utm_source=openai>
