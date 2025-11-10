# Spec: RAG Retriever & Indexer (AI SDK v6)

Overview

- Goal: Define KISS/DRY retriever/indexer contracts for Supabase Postgres + pgvector, hybrid search, and AI SDK v6 Reranking. Ensure reliability, observability, and testability.

Scope

- Indexer: chunking, embeddings upsert, metadata.
- Retriever: query construction (vector + keyword), reranking, assembly for prompts.
- Caching: short TTL with Upstash for popular queries.
- Edge-compat constraints: fetch-only clients in Edge handlers; Node-only ops in Node runtime.

Data model (suggested)

- `documents(id, owner_id, title, source, created_at, metadata jsonb)`
- `chunks(id, document_id, idx, content, metadata jsonb)`
- `embeddings(id, chunk_id, embedding vector(1536), provider, created_at)`

Interfaces (TypeScript)

- `indexer.upsert({ documentId, chunks: { id, content, metadata }[], embeddingModel }) -> Promise<{ upserted: number }>`
- `retriever.search({ query, k, filters?, userId }) -> Promise<{ items: { id, content, score, metadata }[] }>`
- `reranker.rerank({ query, items, model }) -> Promise<{ items: { id, content, score }[] }>`

Design

- Chunking: 512–1,024 tokens; overlap 64.
- Embeddings: provider-selected; persist provider id and dims.
- Hybrid: vector top-N plus keyword BM25 union → score normalization → rerank.
- Reranking: AI SDK v6 Reranking page; prefer Cohere `rerank-v3.5` when available.
- Assembly: cap total tokens via budget selector (from 03-token-budgeting-and-limits.md).

Caching

- Key: `user:{id}:rag:{hash(query)}`; TTL 30–120s depending on provider latency.
- Invalidate on document updates.

Observability

- Spans: `rag.index`, `rag.retrieve`, `rag.rerank` with counts/latency; redact content.

Testing

- Unit: chunking boundaries; embedding payload shape; score merge.
- Integration: search returns stable ordering; rerank improves MRR on fixtures.
- Perf fixtures: latency budgets (< 800ms P50 retrieval+rereank under warm cache).

Acceptance Criteria

- Deterministic ordering with rerank ties broken by recency.
- Edge handlers free of Node-only clients.
- Coverage ≥ 90% for indexer and retriever modules.

References

- AI SDK v6 Reranking: <https://v6.ai-sdk.dev/docs/ai-sdk-core/reranking>
- AI SDK Core Embeddings: <https://v6.ai-sdk.dev/docs/ai-sdk-core/embeddings>
- Upstash Redis Ratelimit/Redis: <https://vercel.com/templates/next.js/ratelimit-with-upstash-redis>
