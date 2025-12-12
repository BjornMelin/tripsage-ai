# SPEC-0018: RAG Retriever & Indexer (AI SDK v6)

**Version**: 2.0.0
**Status**: Implemented
**Date**: 2025-12-12

## Overview

- Goal: Define KISS/DRY retriever/indexer contracts for Supabase Postgres + pgvector, hybrid search, and AI SDK v6 Reranking. Ensure reliability, observability, and testability.

**Current Status:** Full RAG pipeline implemented with:

- Generic indexer endpoint (`POST /api/rag/index`) for batch document indexing
- Retriever endpoint (`POST /api/rag/search`) with hybrid search (vector + lexical)
- Together.ai reranking with Mixedbread `mxbai-rerank-large-v2`
- `ragSearch` agent tool for AI agents
- Database migration for `rag_documents` table with pgvector and hybrid search RPC

## Scope

- Indexer: chunking, embeddings upsert, metadata, namespace support.
- Retriever: query construction (vector + keyword), reranking, assembly for prompts.
- Caching: short TTL with Upstash for popular queries.
- Edge-compat constraints: fetch-only clients in Edge handlers; Node-only ops in Node runtime.

## Data Model (Implemented)

### Tables

- `rag_documents(id UUID PK, content TEXT, embedding vector(1536), metadata JSONB, namespace TEXT, source_id TEXT, chunk_index INT, created_at, updated_at)` — Generic RAG documents with pgvector support, namespace partitioning, and chunking.

### Functions

- `hybrid_rag_search(query_text, query_embedding, filter_namespace, match_count, match_threshold, keyword_weight, semantic_weight)` — Hybrid search combining vector similarity (cosine) with full-text search (BM25/ts_rank).
- `match_rag_documents(query_embedding, filter_namespace, match_threshold, match_count)` — Pure semantic similarity search.

### Indexing

- `rag_documents.embedding` → pgvector **HNSW** (`m=32`, `ef_construction=180`, distance cosine).
- `rag_documents.fts` → GIN index for full-text search (generated tsvector column).
- Namespace index for filtered queries.

## API Endpoints

### POST /api/rag/index

Index documents with automatic chunking and embedding generation.

**Request:**

```typescript
{
  documents: Array<{
    content: string;
    metadata?: Record<string, unknown>;
    id?: string;
    sourceId?: string;
  }>;
  namespace?: string;  // default: "default"
  chunkSize?: number;  // default: 512 token-estimate (~2k chars; model-dependent)
  chunkOverlap?: number;  // default: 100 token-estimate (~400 chars)
}
```

> Note: `batchSize` is an internal indexer setting (default ~10 documents per embedding batch as of 2025-12-12) and is not exposed on the public API.

**Response:**

```typescript
{
  success: boolean;
  indexed: number;
  chunksCreated: number;
  namespace: string;
  total: number;
  failed: Array<{ index: number; error: string }>;
}
```

**Status codes:**

- Always returns `200 OK`, including partial indexing; inspect `success` and `failed` for per-item status.

### POST /api/rag/search

Search documents with hybrid retrieval and optional reranking.

**Request:**

```typescript
{
  query: string;
  namespace?: string;
  limit?: number;  // default: 10
  threshold?: number;  // default: 0.7
  useReranking?: boolean;  // default: true
  keywordWeight?: number;  // default: 0.3
  semanticWeight?: number;  // default: 0.7
}
```

**Response:**

```typescript
{
  success: boolean;
  query: string;
  results: Array<{
    id: string;
    content: string;
    similarity: number;
    keywordRank: number;
    combinedScore: number;
    metadata: Record<string, unknown>;
    namespace: string;
    sourceId: string | null;
    chunkIndex: number;
    rerankScore?: number;
  }>;
  latencyMs: number;
  rerankingApplied: boolean;
}
```

## Agent Tool

### ragSearch

Available to AI agents via the tool registry.

**Input:**

```typescript
{
  query: string;
  namespace?: string;
  limit?: number;
  threshold?: number;
}
```

**Guardrails:**

- Rate limit: 30 requests per minute
- Cache: 5 minutes TTL per query/namespace

## Design Decisions

### Chunking

- Default chunk size (configurable; current code default as of 2025-12-12): 512 tokens (~2k characters)
- Default overlap (configurable; current code default as of 2025-12-12): 100 tokens (~400 characters)
- Sentence boundary detection for clean breaks

### Embeddings

- Provider: OpenAI `text-embedding-3-small` (1536 dimensions)
- Batch processing via AI SDK `embedMany()`

### Hybrid Search

- Default weighting target: ~70% semantic (cosine) / ~30% keyword (ts_rank)
- Configurable weights per request

### Reranking

**Provider:** Together.ai with Mixedbread `mxbai-rerank-large-v2`

| Metric | Value |
|--------|-------|
| Cost | **Estimate**: ~$0.002 per 1k queries (Together.ai pricing as of 2025-12-12) |
| Annual cost (10k/day) | **Estimate**: ~$5–10/year at ~10k queries/day (derived from pricing above; 2025-12-12) |
| Savings vs Cohere | **Estimate**: ~90–97% cheaper vs Cohere rerank pricing (comparison as of 2025-12-12) |
| Quality (ELO) | **Reported**: ~1468 ELO on Mixedbread leaderboard (as of 2025-12-12) |
| Context | 8K token context window (provider spec as of 2025-12-12) |
| Languages | 100+ languages supported (provider spec as of 2025-12-12) |
| AI SDK Support | Native via @ai-sdk/togetherai |

**Fallback:** NoOp reranker returns documents sorted by combined score.
**Timeout target (configurable):** 700ms with graceful degradation.

## Retention & Ownership

- RAG documents tied to namespaces for logical partitioning.
- No automatic cleanup; lifecycle managed by application.
- RLS policies enforce row-level security.

## Caching

- Key: `rag:{namespace}:{hash(query)}`; TTL 300s.
- Invalidate on document updates via namespace.

## Observability

- Spans: `rag.indexer.index_documents`, `rag.retriever.retrieve_documents`, `rag.reranker.together` with counts/latency.
- Telemetry attributes include document counts, namespace, and configuration.

## Testing

### Unit Tests (suite passing in CI; count ~36 as of 2025-12-12)

**indexer.test.ts:**

- Chunking boundaries and overlap
- Sentence boundary detection
- Unicode handling
- Empty/whitespace handling

**reranker.test.ts:**

- TogetherReranker API calls
- NoOpReranker fallback behavior
- Error handling and graceful degradation
- Factory function

**retriever.test.ts:**

- Hybrid search RPC calls
- Embedding generation
- Namespace filtering
- Reranking integration
- Error handling

### Coverage

- Coverage target: ≥85% for RAG modules; verified in CI as of 2025-12-12

## Acceptance Criteria

- [x] Indexer accepts batch documents and stores with embeddings
- [x] Chunking respects 512-1024 token range with overlap
- [x] Hybrid search combines vector + lexical scores
- [x] Together.ai/Mixedbread reranking improves result relevance
- [x] Graceful fallback when reranking fails/times out (timeout target ~700ms; configurable)
- [x] Search latency within budget (P50 target <800ms; measure in CI/staging before release)
- [x] ragSearch tool available to AI agents
- [x] All tests pass and coverage meets ≥85% target
- [x] SPEC-0018 updated to "Implemented" status

## File Inventory

| File | Description |
|------|-------------|
| `src/domain/schemas/rag.ts` | Zod v4 schemas for RAG operations |
| `src/lib/rag/reranker.ts` | Pluggable reranker interface + Together.ai impl |
| `src/lib/rag/indexer.ts` | Document indexing with chunking + embedding |
| `src/lib/rag/retriever.ts` | Hybrid search + reranking logic |
| `supabase/migrations/*_create_rag_documents.sql` | Database migration |
| `src/app/api/rag/index/route.ts` | POST /api/rag/index endpoint |
| `src/app/api/rag/search/route.ts` | POST /api/rag/search endpoint |
| `src/ai/tools/server/rag.ts` | ragSearch agent tool |
| `src/lib/api/rate-limits.ts` | Rate limit configuration |
| `src/lib/rag/__tests__/*.test.ts` | Unit tests |

## References

- AI SDK v6 Reranking: <https://v6.ai-sdk.dev/docs/ai-sdk-core/reranking>
- AI SDK Core Embeddings: <https://v6.ai-sdk.dev/docs/ai-sdk-core/embeddings>
- Together.ai Reranking: <https://v6.ai-sdk.dev/providers/ai-sdk-providers/togetherai#reranking-models>
- Mixedbread mxbai-rerank-large-v2: <https://huggingface.co/mixedbread-ai/mxbai-rerank-large-v2>
