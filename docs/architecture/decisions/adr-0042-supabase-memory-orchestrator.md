# ADR-0042: Supabase-Centric Memory Orchestrator

**Version**: 1.1.0
**Status**: Accepted
**Date**: 2025-12-30
**Category**: Frontend Architecture
**Domain**: AI Memory & Chat Infrastructure
**Related ADRs**: ADR-0002, ADR-0003, ADR-0023, ADR-0031, ADR-0034, ADR-0039
**Related Specs**: SPEC-0026

> **v1.1.0 Update (2025-12-30)**: Removed mem0ai dependency. Supabase adapter now handles semantic search directly via pgvector (`match_turn_embeddings` RPC), eliminating external API calls and 19 optional peer dependencies.

## Context

Recent regressions (see review P1) showed that removing `useChatMemory` hooks broke
all downstream memory sync flows. TripSage's chat store is currently responsible
for appending UI messages *and* calling memory APIs directly. This coupling makes
it impossible to enforce cross-cutting concerns such as PII redaction, retry
semantics, and observability without touching every integration point.

We need a single orchestrator that: (1) treats Supabase Postgres/pgvector as the
canonical long-term memory store with native semantic search; (2) leverages Upstash Redis/QStash for async pipelines, rate-limit guards, and caches; and (3) keeps the Zustand chat store free of
side-effects. This architecture must satisfy AI SDK v6 streaming/tooling flows,
Next.js Cache Components, Supabase SSR auth, and audit/compliance expectations.

## Decision

We will implement a Supabase-centric Memory Orchestrator that exposes intents
(`onTurnCommitted`, `syncSession`, `backfillSession`, `fetchContext`) and routes
them to pluggable adapters:

- **Supabase Adapter (canonical)**: writes chat turns to a `memories` schema,
  persists embeddings via pgvector, enforces Row Level Security, provides semantic
  search via `match_turn_embeddings` RPC, and emits telemetry. This adapter is
  authoritative for replay, analytics, sharing, and context retrieval.
- **Upstash Adapter (queues/caches)**: uses QStash for asynchronous retries and
  Redis/Vector for hot caches or TTL-limited context staging; no user data lives
  here permanently.

All UI/stateful layers (Zustand, hooks, route handlers) emit intents—not direct
provider calls. Feature flags govern adapter enablement, and all requests flow
through centralized PII filters plus OpenTelemetry spans.

### Vector indexing, retention, and session reuse

- **PII handling in embeddings:** redact PII **before** embedding generation using the existing orchestrator PII filters; embeddings are created from redacted text only. User deletion requests must cascade to `memories.turn_embeddings` (ON DELETE CASCADE) and trigger explicit embedding cleanup. Embedding storage follows GDPR/CCPA: no long-term retention of identifiers inside vectors.
- **Indexes:** Use pgvector **HNSW** for latency-sensitive stores:
  - `accommodation_embeddings.embedding` and `memories.turn_embeddings.embedding`
    with `m=${PGVECTOR_HNSW_M:-32}`, `ef_construction=${PGVECTOR_HNSW_EF_CONSTRUCTION:-180}` (160 acceptable on RAM-tight nodes),
    default `ef_search=${PGVECTOR_HNSW_EF_SEARCH_DEFAULT:-96}`; target range 64–128 based on workload. These defaults balance recall/latency for 1536-d embeddings (OpenAI text-embedding-3-small) under current traffic.
  - Fallback (if write-heavy / memory constrained): IVFFlat with `lists≈500–1000`,
    `probes≈20`; document when chosen.
- **Query functions:** `match_accommodation_embeddings` sets `hnsw.ef_search` from `PGVECTOR_HNSW_EF_SEARCH_DEFAULT` at runtime and accepts an optional `ef_search_override` for per-call tuning; operators can observe recall/latency with EXPLAIN ANALYZE and `pg_stat_user_indexes`.
- **Retention:** `memories.turn_embeddings` cleaned up at **${MEMORIES_RETENTION_DAYS:-180} days** via pg_cron; align embeddings and session records to the same window. Rationale: matches product UX (recent travel context) and privacy expectations; configurable via `MEMORIES_RETENTION_DAYS` for regulatory changes. Deploy the cron job in migrations; monitor via Postgres logs; ship Datadog alerts in issue #520.
- **Session semantics:** reuse the most recent "Travel Plan" chat/memory session **per user** when the planner tool is invoked to reduce fragmentation and improve retrieval accuracy. Session-level locking for concurrent invocations now guards session creation (Redis lock in `src/ai/tools/server/planning.ts`). Users can start a fresh session by clearing memory or opening a new chat thread.

### Implementation status & follow-ups (tracked)

- [x] **Config surface** — Parameterize pgvector/HNSW + retention defaults in migrations (issue [#517](https://github.com/BjornMelin/tripsage-ai/issues/517), completed 2025-12-22).
- [ ] **`ef_search_override`** — Wire optional override through `match_accommodation_embeddings` and adapters (issue [#518](https://github.com/BjornMelin/tripsage-ai/issues/518)). RPC parameter exists; adapter wiring pending.
- [x] **Session-level locking** — Implemented via Redis token lock in `src/ai/tools/server/planning.ts`.
- [ ] **Monitoring** — Ship alerts for retention cron + HNSW maintenance jobs (issue [#520](https://github.com/BjornMelin/tripsage-ai/issues/520)). Infrastructure pending.

## Consequences

### Positive

- Canonical, queryable memory with Supabase pgvector + RLS.
- Native semantic search via `match_turn_embeddings` RPC eliminates external API calls.
- Pluggable adapters allow rapid provider experiments without touching UI code.
- Observability & retries centralized (QStash, OTLP), reducing silent failures.
- Compliance improvements: PII redaction + scoped schemas.
- Reduced dependency surface (removed mem0ai and 19 optional peer dependencies).

### Negative

- Additional orchestration layer introduces upfront complexity and schema work.
- Requires coordinated migrations (Supabase schema, queue topics, feature flags).

### Neutral

- Local persistence (Zustand + storage) stays for offline UX but no longer
  determines canonical truth; sync lag is acceptable by design.
- Existing AI SDK routes continue to work; orchestrator simply wraps them.

## Alternatives Considered

### Option A – Mem0-Managed Memory

Fastest integration via the Mem0 Vercel AI SDK provider, but it creates a single
vendor dependency lacking relational queries, pgvector analytics, or Supabase
auditing. Lock-in risk and opaque retry semantics led us to reject it.

> **Note (v1.1.0)**: An initial Mem0 adapter was implemented but deprecated in
> favor of native Supabase pgvector semantic search via `match_turn_embeddings`
> RPC. This eliminated external API dependencies and reduced the package surface.

### Option B – Upstash Redis/Vector + QStash Only

Serverless-friendly and low-op, yet it forces us to encode relational metadata
inside Redis keyspaces and manage TTL churn for every long-term memory. Without
Supabase, we lose SQL-based personalization, RLS, and analytics.

## References

- Supabase Vector functions & embeddings – <https://supabase.com/modules/vector?utm_source=openai>
- Upstash AI SDK/Vector patterns – <https://upstash.com/blog/vercel-ai-sdk?utm_source=openai>
- TripSage ADRs: ADR-0002 (Supabase platform), ADR-0003 (Upstash Redis),
  ADR-0023 (AI SDK v6), ADR-0031 (Chat API), ADR-0039 (Frontend agent modernization).
