# Supabase Memory Orchestrator Implementation Prompt

## Executive Summary

- **Objective**: Implement the Supabase-centric Memory Orchestrator defined in ADR-0042 and SPEC-0026. Supabase Postgres/pgvector becomes the canonical conversation-memory store, while Mem0 (optional) and Upstash Redis/QStash act as enrichment & queue layers.
- **Drivers**: Prevent regressions caused by UI stores invoking memory backends directly, enable multi-provider experiments, strengthen compliance (RLS, PII redaction), and reach ≥9/10 weighted architecture score.

## Key References

- ADR-0042 (`docs/adrs/adr-0042-supabase-memory-orchestrator.md`).
- SPEC-0026 (`docs/specs/0026-spec-supabase-memory-orchestrator.md`).
- Supabase Vector module: <https://supabase.com/modules/vector?utm_source=openai>.
- Mem0 + Vercel AI SDK integration: <https://docs.mem0.ai/integrations/vercel-ai-sdk?utm_source=openai>.
- Upstash AI SDK patterns: <https://upstash.com/blog/vercel-ai-sdk?utm_source=openai>.

## Decision Framework Snapshot

| Option | Solution Leverage 35% | Application Value 30% | Maintenance 25% | Adaptability 10% | Weighted |
| --- | --- | --- | --- | --- | --- |
| Mem0-only | 6.8 | 6.6 | 8.4 | 5.5 | 7.10 |
| Upstash-first | 7.6 | 7.8 | 6.5 | 7.2 | 7.45 |
| **Supabase canonical (chosen)** | **9.2** | **9.0** | **8.8** | **9.3** | **9.05** |

## Files & Directories to Load

- `frontend/src/stores/chat/chat-messages.ts` (intents emitter).
- `frontend/src/lib/memory/` *(new directory)* for orchestrator + adapters.
- `frontend/src/lib/providers/registry.ts` (reuse provider resolution).
- `frontend/src/lib/supabase/server.ts` + `frontend/src/lib/supabase/clients/**` (service-role clients).
- `frontend/src/lib/chat/api-client.ts` & route handlers under `frontend/src/app/api/**` (wire orchestrator calls).
- New Supabase SQL migration files under `migrations/supabase` (`memories` schema, pgvector indexes, RLS policies).
- `docs/adrs/adr-0042-supabase-memory-orchestrator.md`, `docs/specs/0026-spec-supabase-memory-orchestrator.md` for acceptance criteria.
- Observability config (`frontend/src/lib/otel/**`).
- Testing harnesses: `frontend/src/stores/__tests__`, `frontend/src/lib/__tests__`, Playwright specs.

## Implementation Plan

1. **Schema & Infrastructure**
   - Create `memories.sessions`, `memories.turns`, `memories.turn_embeddings` via Supabase migration scripts (SQL per SPEC-0026).
   - Enable pgvector extension (if not already) and build service-role Edge Function for embedding refresh.
   - Define RLS policies keyed on `user_id`; schedule pg_cron/pgmq tasks for retrying stuck syncs.
2. **Memory Orchestrator Module** (`frontend/src/lib/memory/orchestrator.ts`)
   - Define `MemoryIntent`, `MemoryAdapter`, context & result types.
   - Implement orchestrator pipeline: validation, redaction helpers, OTLP spans, adapter fan-out, feature flags.
   - Provide configuration hooks (env or `config/memory.ts`) for toggling adapters.
3. **Adapters**
   - `supabase-adapter.ts`: insert/update rows, request embeddings (Edge Function call), return canonical IDs.
   - `upstash-adapter.ts`: publish to QStash topics, manage Redis caches, expose retry helpers.
   - `mem0-adapter.ts`: wrap `createMem0()` (AI SDK v6) to push curated turns & fetch context snapshots.
4. **Chat Store & Hooks**
   - Update `useChatMessages` to emit orchestrator intents after each user/assistant turn (`onTurnCommitted`) instead of calling `useChatMemory` directly.
   - Ensure streaming flows call `syncSession` on completion; remove legacy cross-store dependencies once parity verified.
5. **Route Handlers**
   - Refactor `/api/chat`, `/api/chat/stream`, and any agent routes that currently enqueue `/api/memory/sync` to call orchestrator functions.
   - Provide fallback message if orchestrator returns errors; log telemetry.
6. **Security & Observability**
   - Integrate PII redaction module before non-Supabase adapters; store hashed metadata for auditing.
   - Emit OTLP spans per adapter with status attributes.
7. **Testing & Validation**
   - Unit tests for orchestrator + adapters (Vitest).
   - Integration tests hitting Supabase test instance + Upstash mock + Mem0 stub.
   - Playwright regression verifying conversation recall.
   - Load test harness to measure latency (<250 ms median orchestrator time).
8. **Rollout**
   - Introduce feature flag `memory.orchestrator.enabled` (config + env).
   - Shadow mode: emit intents + legacy sync simultaneously, compare metrics.
   - Cut over once failures <0.1%; remove legacy `useChatMemory` store coupling.

## Deliverables

- Supabase migration scripts + runbook updates (`docs/operators/` if needed).
- TypeScript orchestrator/adapters with tests.
- Updated documentation (README snippets, ADR/Spec references already in repo).
- Monitoring dashboards/alerts for memory sync health.
- Verification checklist for QA + release management.

## Additional Notes

- Keep provider credentials in the existing provider registry (ADR-0028) to avoid duplicating env lookups.
- Coordinate with Ops to provision QStash topics + DLQ before enabling Upstash adapter.
- Document rollback plan: disable flag, revert migration if necessary.
