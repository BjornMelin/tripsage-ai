# SPEC-0104: Memory and RAG (Supabase pgvector + reranking)

**Version**: 1.0.0  
**Status**: Final  
**Date**: 2026-01-05

## Goals

- Users can store and retrieve “memories”:
  - trip notes, preferences, uploads, inferred constraints
- RAG search supports:
  - hybrid retrieval (vector + lexical)
  - reranking
  - short TTL caching for repeated queries

## Data model

Canonical schema:

- Database migration: `supabase/migrations/20251211000000_create_rag_documents.sql`
- Zod schemas and request/response types: `src/domain/schemas/rag.ts`

Tables and indexes (implementation):

- `rag_documents`
  - `id` UUID (primary key), chunked with `chunk_index` for lineage
  - `content` TEXT
  - `embedding` vector(1536) (OpenAI `text-embedding-3-small`)
  - `metadata` JSONB (arbitrary filter/context fields)
  - `namespace` TEXT (constrained to a fixed enum)
  - `source_id` TEXT (lineage back to an original source)
  - `fts` tsvector (generated) + GIN index for lexical matching
  - HNSW index for cosine similarity search on `embedding`

## API

Route Handlers:

- POST /api/rag/index
- POST /api/rag/search

Requests and responses:

- `/api/rag/index`
  - Body: `ragIndexRequestSchema`
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

- Embeddings use OpenAI `text-embedding-3-small` (1536 dimensions).
- Hybrid retrieval uses the `hybrid_rag_search` RPC (vector + lexical).
- Reranking is optional (`useReranking`) and uses Together.ai with a ~700ms timeout; failures fall back to the original ranking.

## Caching

- Query-level caching is optional and should be short-lived (seconds to minutes) and scoped to user + namespace.
- Cache key should include at least: `userId`, `namespace`, and a stable hash of `query + weights + threshold + limit`.
- Never cache secrets or store raw documents outside the RAG tables.

## Safety

- Never index secrets.
- Namespaces are logical partitions and must not be treated as an authorization boundary.
- RLS is enabled on `rag_documents` (see the migration); ensure policies match the desired exposure (anonymous vs. authenticated) for the deployment.

## References

```text
Supabase pgvector guide: https://supabase.com/docs/guides/ai/vector-columns
AI SDK RAG patterns: https://ai-sdk.dev/docs/ai-sdk-core
```
