# SPEC-0018: RAG Retriever & Indexer (AI SDK v6)

**Version**: 1.0.0  
**Status**: Partial (Embeddings Only)  
**Date**: 2025-11-04

## Overview

- Goal: Define KISS/DRY retriever/indexer contracts for Supabase Postgres + pgvector, hybrid search, and AI SDK v6 Reranking. Ensure reliability, observability, and testability.

**Current Status:** Embeddings generation endpoint (`POST /api/embeddings`) is implemented using AI SDK v6 `embed()` with OpenAI `text-embedding-3-small` (1536-d). Accommodation embeddings are persisted to `accommodation_embeddings` table with pgvector. Full retriever/indexer pipeline (chunking, hybrid search, reranking) is not yet implemented.

## Scope

- Indexer: chunking, embeddings upsert, metadata.
- Retriever: query construction (vector + keyword), reranking, assembly for prompts.
- Caching: short TTL with Upstash for popular queries.
- Edge-compat constraints: fetch-only clients in Edge handlers; Node-only ops in Node runtime.

## Data model (Current Implementation)

- `accommodation_embeddings(id TEXT PK, source TEXT, name TEXT, description TEXT, amenities TEXT, embedding vector(1536), created_at, updated_at)` — Accommodation-specific embeddings with pgvector support.
- `match_accommodation_embeddings(query_embedding vector(1536), match_threshold FLOAT, match_count INT)` — PostgreSQL function for semantic similarity search.

**Indexing (current)**

- `accommodation_embeddings.embedding` → pgvector **HNSW** (`m=32`, `ef_construction=180`, distance L2); per-query `hnsw.ef_search` default 96 (tune 64–128).
- `memories.turn_embeddings.embedding` → pgvector **HNSW** (`m=32`, `ef_construction=180`). Fallback if write-heavy: IVFFlat (`lists≈500–1000`, `probes≈20`).

## Data model (Target - Not Yet Implemented)

- `documents(id, owner_id, title, source, created_at, metadata jsonb)`
- `chunks(id, document_id, idx, content, metadata jsonb)`
- `embeddings(id, chunk_id, embedding vector(1536), provider, created_at)`

## Interfaces (TypeScript)

- `indexer.upsert({ documentId, chunks: { id, content, metadata }[], embeddingModel }) -> Promise<{ upserted: number }>`
- `retriever.search({ query, k, filters?, userId }) -> Promise<{ items: { id, content, score, metadata }[] }>`
- `reranker.rerank({ query, items, model }) -> Promise<{ items: { id, content, score }[] }>`

## Design

- Chunking: 512–1,024 tokens; overlap 64.
- Embeddings: provider-selected; persist provider id and dims.
- Hybrid: vector top-N plus keyword BM25 union → score normalization → rerank.
- Reranking: AI SDK v6 Reranking page; prefer Cohere `rerank-v3.5` when available.
- Assembly: cap total tokens via budget selector (from [SPEC-0013](../archive/0013-token-budgeting-and-limits.md)).

### Index strategy & migrations

- Default new vector stores to HNSW (parameters above) unless the table is heavily write-biased, in which case IVFFlat with `lists≈500–1000`, `probes≈20` is acceptable.
- Zero-downtime migration pattern: create new HNSW index concurrently, update query functions to set `hnsw.ef_search`, validate latency/recall, then drop the legacy IVFFlat index.
- When embedding dimensions or providers change, dual-write to a new column/index, backfill, and version the query function before cutting over.

### Retention & ownership

- Embeddings tied to chat turns adhere to the **180-day** cleanup job (pg_cron) and should carry `created_at` plus optional `expires_at` for enforcement.
- All retriever/indexer writes must include `owner_id` (or tenant key) and rely on SQL RLS; `userId` is required unless content is explicitly public.

## Caching

- Key: `user:{id}:rag:{hash(query)}`; TTL 30-120s depending on provider latency.
- Invalidate on document updates.

## Observability

- Spans: `rag.index`, `rag.retrieve`, `rag.rerank` with counts/latency; redact content.

## Testing

- Unit: chunking boundaries; embedding payload shape; score merge.
- Integration: search returns stable ordering; rerank improves MRR on fixtures.
- Perf fixtures: latency budgets (< 800ms P50 retrieval+rerank under warm cache).

## Acceptance Criteria

- Deterministic ordering with rerank ties broken by recency.
- Edge handlers free of Node-only clients.
- Coverage ≥ 90% for indexer and retriever modules.

## References

- AI SDK v6 Reranking: <https://v6.ai-sdk.dev/docs/ai-sdk-core/reranking>
- AI SDK Core Embeddings: <https://v6.ai-sdk.dev/docs/ai-sdk-core/embeddings>
- Upstash Redis Ratelimit/Redis: <https://vercel.com/templates/next.js/ratelimit-with-upstash-redis>
