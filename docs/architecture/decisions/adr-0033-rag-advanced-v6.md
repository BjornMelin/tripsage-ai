# ADR-0033: RAG advanced (hybrid retrieval + Upstash caching + Together reranking)

**Version**: 1.0.0  
**Status**: Accepted  
**Date**: 2026-01-19  
**Category**: Architecture  
**Domain**: Memory + RAG  
**Related ADRs**: ADR-0023, ADR-0032, ADR-0067  
**Related Specs**: SPEC-0104

## Context

TripSage needs a production-grade RAG pipeline implemented in the Next.js 16 codebase:

- Store chunked documents in Supabase Postgres with pgvector (`vector(1536)`) and fast similarity search (HNSW).
- Provide hybrid retrieval (vector + lexical) to improve recall and robustness.
- Optionally rerank retrieved chunks for higher relevance.
- Keep local development and tests fully runnable without requiring API keys.
- Bound cost and latency using short-lived caching and timeouts.

## Decision

We will:

1) **Standardize on `vector(1536)`** for all persisted embeddings and pgvector RPCs, aligned to OpenAI `text-embedding-3-small` dimensions.

2) **Use AI SDK v6 embeddings (`embed`, `embedMany`)** with a deterministic model-selection strategy:

   - If `AI_GATEWAY_API_KEY` is configured, use the AI SDK string model id `openai/text-embedding-3-small`.
   - Else if `OPENAI_API_KEY` is configured, use `openai.embeddingModel("text-embedding-3-small")`.
   - Else, use a deterministic local fallback embedding model that returns 1536-d vectors for offline dev/tests.

   This is implemented in `src/lib/ai/embeddings/text-embedding-model.ts`.

3) **Use hybrid retrieval** via Supabase RPC `hybrid_rag_search` in `supabase/migrations/20260120000000_base_schema.sql`, and generate the query embedding using `embed()` in `src/lib/rag/retriever.ts`.

   - Indexing uses `embedMany()` with `maxParallelCalls` (default: 2) to bound concurrency and reduce provider/rate-limit pressure during bulk indexing.

4) **Use AI SDK v6 reranking (`rerank`) via Together.ai** when enabled:

   - Reranking provider: Together.ai via `@ai-sdk/togetherai`.
   - Model: `mixedbread-ai/Mxbai-Rerank-Large-V2`.
   - Controlled by `useReranking` and the presence of `TOGETHER_AI_API_KEY`.
   - If `TOGETHER_AI_API_KEY` is unset, reranking degrades to a no-op reranker (no repeated provider errors; no extra cost).

   This is implemented in `src/lib/rag/reranker.ts`.

5) **Add user-scoped, content-free Upstash caching** for RAG search results:

   - Cache key includes a user hash + request parameters + embedding model id to avoid cross-user leakage and stale results.
   - Cache TTL is short (currently 120 seconds).
   - Cache entries store only ids + scores + `chunkIndex` and are rehydrated from `public.rag_documents`.

   This is implemented in `src/app/api/rag/search/_handler.ts`.

6) **Add provider call timeouts** using `AbortSignal.timeout(...)` for embeddings/reranking so serverless requests cannot hang indefinitely.

## Consequences

### Positive

- RAG retrieval and indexing remain aligned with production (`vector(1536)`) while still allowing local/offline dev and CI.
- Reranking is optional and fails safely without breaking RAG search.
- Cost is bounded via short TTL caching and strict chunk limits.

### Negative

- The deterministic fallback embeddings are not semantically meaningful; meaningful relevance testing locally requires `AI_GATEWAY_API_KEY` or `OPENAI_API_KEY`.

### Neutral

- Reranking adds a second provider surface area (Together.ai) but is cleanly isolated behind a `Reranker` interface.

## Alternatives Considered

### Local semantic embeddings (Ollama / transformers.js)

Rejected for now because the system is standardized on `vector(1536)`:

- Most practical local embedding models output 384/768/1024 dimensions, which is incompatible with `vector(1536)` indexes and RPC signatures without padding/projection or maintaining dual indexes.
- Dimension transforms break dev/prod parity and increase maintenance surface area.

If offline semantic search becomes a hard requirement, the correct approach is a deliberate schema + index strategy for dual embedding spaces rather than ad-hoc transformations.

## References

- AI SDK v6 embeddings: <https://ai-sdk.dev/docs/ai-sdk-core/embeddings>  
- AI SDK v6 `embed()` reference: <https://ai-sdk.dev/docs/reference/ai-sdk-core/embed>  
- AI SDK v6 `embedMany()` reference: <https://ai-sdk.dev/docs/reference/ai-sdk-core/embed-many>  
- AI SDK v6 `rerank()` reference: <https://ai-sdk.dev/docs/reference/ai-sdk-core/rerank>  
- AI SDK AI Gateway provider: <https://ai-sdk.dev/providers/ai-sdk-providers/ai-gateway>  
- Upstash Ratelimit (TS) features (dynamic limits, caching, pending): <https://upstash.com/docs/redis/sdks/ratelimit-ts/features>  
- Upstash Ratelimit (TS) methods (dynamic limits APIs): <https://upstash.com/docs/redis/sdks/ratelimit-ts/methods>  
- Upstash Ratelimit v2.0.8 release notes: <https://github.com/upstash/ratelimit-js/releases/tag/v2.0.8>  
- OpenAI API pricing (embeddings): <https://platform.openai.com/docs/pricing>  
- Together.ai pricing (rerank): <https://www.together.ai/pricing>  
