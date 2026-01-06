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

## Data model (minimum)

- rag_documents
  - id, user_id, trip_id nullable, namespace, content, metadata JSONB
  - embedding vector
  - created_at
- rag_sources
  - source_id, type (attachment, note, web), ref

## API

Route Handlers:

- POST /api/rag/index
- POST /api/rag/search

Agent tool:

- rag.search({ query, tripId?, chatId?, namespace? })

## Safety

- Never index secrets.
- Use user-scoped namespaces by default.
- Enforce RLS on all RAG tables.

## References

```text
Supabase pgvector guide: https://supabase.com/docs/guides/ai/vector-columns
AI SDK RAG patterns: https://ai-sdk.dev/docs/ai-sdk-core
```
