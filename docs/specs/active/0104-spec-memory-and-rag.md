# SPEC-0104: Memory and RAG (Supabase pgvector + embeddings + reranking)

**Version**: 1.1.0  
**Status**: Final  
**Date**: 2026-01-19

## Goals

- Users can store and retrieve “memories”:
  - trip notes, preferences, uploads, inferred constraints
- RAG search supports:
  - hybrid retrieval (vector + lexical)
  - reranking
  - short TTL caching for repeated queries (cost/latency control)
- Local development is fully runnable without paid provider keys:
  - deterministic embeddings fallback for offline/dev/test
  - reranking degrades to no-op if Together is not configured

## Data model

Canonical schema:

- Database migration: `supabase/migrations/20260120000000_base_schema.sql`
- Zod schemas and request/response types: `src/domain/schemas/rag.ts`

Tables and indexes (implementation):

- `rag_documents`
  - Primary key: `(id, chunk_index)`
    - `id` is the stable “document id” (lineage across chunks)
    - `chunk_index` is the 0-based chunk position within that document
  - `content` TEXT
  - `embedding` vector(1536) (standard dimension for the system; matches OpenAI `text-embedding-3-small`)
  - `metadata` JSONB (arbitrary filter/context fields)
  - `namespace` TEXT (constrained to a fixed enum)
  - `source_id` TEXT (lineage back to an original source)
  - `fts` tsvector (generated) + GIN index for lexical matching
  - HNSW index for cosine similarity search on `embedding`

## API

Route Handlers:

- POST /api/rag/index
- POST /api/rag/search
- POST /api/embeddings (internal-only; optional persistence of embeddings into `accommodation_embeddings`)

Requests and responses:

- `/api/rag/index`
  - Body: `ragIndexRequestSchema`
    - `maxParallelCalls` (optional, default `2`): bounds `embedMany()` concurrency during indexing.
  - Response: `ragIndexResponseSchema` (HTTP 200; partial success via `success: false` and per-item failures)
- `/api/rag/search`
  - Body: `ragSearchRequestSchema`
  - Response: `ragSearchResponseSchema` (includes scores, `rerankingApplied`, and `latencyMs`)

Auth and limits:

- Both endpoints require authentication and are rate-limited via `withApiGuards` (`rag:index`, `rag:search`).

Agent tool:

- rag.search({ query, namespace?, limit?, threshold? }) → `RagSearchToolOutput`
  - Input: `ragSearchInputSchema`
  - Output: `ragSearchToolOutputSchema` / `RagSearchToolOutput`

## Retrieval behavior

### Embeddings (AI SDK v6)

- Embeddings are generated via AI SDK v6 `embed()` / `embedMany()` and stored as `vector(1536)` in Postgres.
- The embedding model selection is server-only and deterministic:
  - If `AI_GATEWAY_API_KEY` is set, use string model id `openai/text-embedding-3-small`.
  - Else if `OPENAI_API_KEY` is set, use `openai.embeddingModel("text-embedding-3-small")`.
  - Else, use a deterministic local fallback embedding model (1536-d) for offline dev/tests.
- **Important**: The deterministic fallback is not semantically meaningful; it exists to keep local dev + CI runnable without keys.
- Indexing uses `embedMany()` with `maxParallelCalls` (default: 2) to bound concurrency and reduce provider/rate-limit pressure during bulk indexing.

Implementation:

- Model selection: `src/lib/ai/embeddings/text-embedding-model.ts`
- RAG indexer: `src/lib/rag/indexer.ts` (uses `embedMany`)
- RAG retriever: `src/lib/rag/retriever.ts` (uses `embed`)
- Memory semantic retrieval: `src/lib/memory/supabase-adapter.ts`

### Hybrid retrieval (Supabase RPC)

- Hybrid retrieval uses the `hybrid_rag_search` RPC (vector + lexical).
- Pure semantic search uses `match_rag_documents` (vector only).
- Default `threshold` is `0.0` so that deterministic fallback embeddings can still return non-empty results in local dev/CI. Production deployments should tune `threshold` upward to reduce noise.

### Reranking (AI SDK v6)

- Reranking is optional (`useReranking`) and uses AI SDK v6 `rerank()` via Together.ai:
  - Model: `mixedbread-ai/Mxbai-Rerank-Large-V2`
  - Timeout: ~700ms (configurable)
- If `TOGETHER_AI_API_KEY` is unset, reranking degrades to a no-op reranker (results are returned by hybrid ranking only).

## Caching

- Query-level caching is optional and should be short-lived (seconds to minutes) and scoped to user + namespace.
- Cache key should include at least: `userId`, `namespace`, and a stable hash of `query + weights + threshold + limit`.
- Never cache secrets or store raw documents outside the RAG tables.

### RAG search cache (implemented)

- `/api/rag/search` uses Upstash Redis caching with:
  - TTL: 120 seconds
  - Scope: per user (hash of `userId`)
  - Input hash: includes query + weights + threshold + limit + `useReranking` + embedding model id
  - Stored payload: ids + scores + `chunkIndex` only (no `content`)
  - On cache hit: rehydrates `content/metadata/namespace/source_id` from `public.rag_documents`
  - Cache is best-effort: Upstash errors are treated as `miss/unavailable` so the request still succeeds without Redis (errors are recorded in telemetry with sanitized messages; raw keys are not logged)

Implementation: `src/app/api/rag/search/_handler.ts`.

## Local development (Supabase + deterministic seed profiles)

### Bootstrap

```bash
pnpm supabase:bootstrap
pnpm supabase:status
```

Populate `.env.local` with the local Supabase URL + keys printed by `pnpm supabase:status`.

### Deterministic seed datasets

- `pnpm supabase:reset:dev` — general UI dev dataset
- `pnpm supabase:reset:e2e` — minimal deterministic dataset for Playwright flows
- `pnpm supabase:reset:payments` — Stripe/payments-focused dataset
- `pnpm supabase:reset:calendar` — calendar/OAuth-focused dataset
- `pnpm supabase:reset:edge-cases` — error paths + validation edge cases

Seed implementation: `scripts/seed/supabase-local.ts` (+ fixtures in `scripts/seed/fixtures/`).

### Provider keys (when you need real semantic relevance locally)

- For real semantic retrieval/relevance testing, configure at least one embedding provider:
  - `AI_GATEWAY_API_KEY` (preferred for team fallback), or
  - `OPENAI_API_KEY` (direct)
- For reranking, configure:
  - `TOGETHER_AI_API_KEY` (optional; reranking is otherwise a no-op)

## Safety

- Never index secrets.
- Namespaces are logical partitions and must not be treated as an authorization boundary.
- RLS is enabled on `rag_documents` (see the migration); ensure policies match the desired exposure (anonymous vs. authenticated) for the deployment.

## Cost model (rough estimates)

### Embeddings cost (OpenAI)

OpenAI pricing changes over time. Refer to the official pricing page for current rates for `text-embedding-3-small` (and any batch pricing, if applicable).

Rule of thumb:

- 1 token ≈ 4 characters (English prose).
- Chunking defaults: 512 tokens with 100-token overlap.

Estimated cost to embed N chunks:

- Cost ≈ (total_input_tokens / 1_000_000) * (current $/1M tokens)

### Reranking cost (Together.ai)

Together rerank pricing changes over time. Refer to the official pricing page for current rates for `mixedbread-ai/Mxbai-Rerank-Large-V2` (or the configured rerank model).

Cost drivers:

- Reranking processes the query + selected documents text.
- This is why retrieval uses short TTL caching and defaults to a small top-N.

## References

```text
Supabase pgvector guide: https://supabase.com/docs/guides/database/extensions/pgvector
AI SDK RAG patterns: https://ai-sdk.dev/docs/ai-sdk-core
AI SDK embeddings guide: https://ai-sdk.dev/docs/ai-sdk-core/embeddings
AI SDK embed(): https://ai-sdk.dev/docs/reference/ai-sdk-core/embed
AI SDK embedMany(): https://ai-sdk.dev/docs/reference/ai-sdk-core/embed-many
AI SDK rerank(): https://ai-sdk.dev/docs/reference/ai-sdk-core/rerank
AI SDK reranking guide: https://ai-sdk.dev/docs/ai-sdk-core/reranking
AI SDK AI Gateway provider: https://ai-sdk.dev/providers/ai-sdk-providers/ai-gateway
Upstash Ratelimit TS features: https://upstash.com/docs/redis/sdks/ratelimit-ts/features
Upstash Ratelimit TS methods: https://upstash.com/docs/redis/sdks/ratelimit-ts/methods
OpenAI pricing: https://platform.openai.com/docs/pricing
Together.ai pricing: https://www.together.ai/pricing
```
