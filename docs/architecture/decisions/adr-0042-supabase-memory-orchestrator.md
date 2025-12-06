# ADR-0042: Supabase-Centric Memory Orchestrator

**Version**: 1.0.0  
**Status**: Accepted  
**Date**: 2025-11-18  
**Category**: Frontend Architecture  
**Domain**: AI Memory & Chat Infrastructure  
**Related ADRs**: ADR-0002, ADR-0003, ADR-0023, ADR-0031, ADR-0034, ADR-0039  
**Related Specs**: SPEC-0026

## Context

Recent regressions (see review P1) showed that removing `useChatMemory` hooks broke
all downstream memory sync flows. TripSage’s chat store is currently responsible
for appending UI messages *and* calling memory APIs directly. This coupling makes
it impossible to experiment with alternative providers (Mem0, Upstash Vector,
Supabase pgvector) or to enforce cross-cutting concerns such as PII redaction,
retry semantics, and observability.

We need a single orchestrator that: (1) treats Supabase Postgres/pgvector as the
canonical long-term memory store; (2) optionally enriches retrieval with managed
services like Mem0; (3) leverages Upstash Redis/QStash for async pipelines,
rate-limit guards, and caches; and (4) keeps the Zustand chat store free of
side-effects. This architecture must satisfy AI SDK v6 streaming/tooling flows,
Next.js Cache Components, Supabase SSR auth, and audit/compliance expectations.

## Decision

We will implement a Supabase-centric Memory Orchestrator that exposes intents
(`onTurnCommitted`, `syncSession`, `backfillSession`, `fetchContext`) and routes
them to pluggable adapters:

- **Supabase Adapter (canonical)**: writes chat turns to a `memories` schema,
  persists embeddings via pgvector, enforces Row Level Security, and emits
  telemetry. This adapter is authoritative for replay, analytics, and sharing.
- **Upstash Adapter (queues/caches)**: uses QStash for asynchronous retries and
  Redis/Vector for hot caches or TTL-limited context staging; no user data lives
  here permanently.
- **Mem0 Adapter (optional retrieval)**: enriches context by pushing curated
  turns to Mem0’s AI SDK v6 provider, but never serves as primary storage.

All UI/stateful layers (Zustand, hooks, route handlers) emit intents—not direct
provider calls. Feature flags govern adapter enablement, and all requests flow
through centralized PII filters plus OpenTelemetry spans.

### Vector indexing, retention, and session reuse

- **Indexes:** Use pgvector **HNSW** for latency-sensitive stores:
  - `accommodation_embeddings.embedding` and `memories.turn_embeddings.embedding`
    with `m=32`, `ef_construction=180` (160 acceptable on RAM-tight nodes),
    `ef_search` default `96` (tune 64–128 per query).
  - Fallback (if write-heavy / memory constrained): IVFFlat with `lists≈500–1000`,
    `probes≈20`; document when chosen.
- **Query functions:** set `hnsw.ef_search` per call (see `match_accommodation_embeddings`).
- **Retention:** `memories.turn_embeddings` cleaned up at **180 days** via pg_cron;
  align embeddings and sessions to the same window.
- **Session semantics:** reuse an existing "Travel Plan" chat/memory session when
  the planner tool is invoked, rather than creating a new session per call, to
  reduce fragmentation and keep retrieval accuracy high.

## Consequences

### Positive

- Canonical, queryable memory with Supabase pgvector + RLS.
- Pluggable adapters allow rapid provider experiments without touching UI code.
- Observability & retries centralized (QStash, OTLP), reducing silent failures.
- Compliance improvements: PII redaction + scoped schemas before external calls.

### Negative

- Additional orchestration layer introduces upfront complexity and schema work.
- Requires coordinated migrations (Supabase schema, queue topics, feature flags).
- Mem0 usage remains best-effort; teams must monitor provider quotas separately.

### Neutral

- Local persistence (Zustand + storage) stays for offline UX but no longer
  determines canonical truth; sync lag is acceptable by design.
- Existing AI SDK routes continue to work; orchestrator simply wraps them.

## Alternatives Considered

### Option A – Mem0-Managed Memory

Fastest integration via the Mem0 Vercel AI SDK provider, but it creates a single
vendor dependency lacking relational queries, pgvector analytics, or Supabase
auditing. Lock-in risk and opaque retry semantics led us to reject it.

### Option B – Upstash Redis/Vector + QStash Only

Serverless-friendly and low-op, yet it forces us to encode relational metadata
inside Redis keyspaces and manage TTL churn for every long-term memory. Without
Supabase, we lose SQL-based personalization, RLS, and analytics.

## References

- Mem0 Vercel AI SDK integration guide – <https://docs.mem0.ai/integrations/vercel-ai-sdk?utm_source=openai>  
- Upstash AI SDK/Vector patterns – <https://upstash.com/blog/vercel-ai-sdk?utm_source=openai>  
- Supabase Vector functions & embeddings – <https://supabase.com/modules/vector?utm_source=openai>  
- TripSage ADRs: ADR-0002 (Supabase platform), ADR-0003 (Upstash Redis),
  ADR-0023 (AI SDK v6), ADR-0031 (Chat API), ADR-0039 (Frontend agent modernization).
