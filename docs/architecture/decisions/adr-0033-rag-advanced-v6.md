# ADR: RAG Advanced with AI SDK v6 (Hybrid + Provider Reranking)

## Status

Proposed

## Context

We need a robust RAG pipeline on Next.js 16 using AI SDK v6. Python RAG remains in FastAPI; we will unify in TypeScript with Supabase pgvector, hybrid retrieval (vector + keyword), and provider reranking (e.g., Cohere).

## Decision

- Adopt hybrid retrieval in TS and apply provider reranking (e.g., cohere.reranking('rerank-v3.5')) for top-k refinement. Provider-dependent feature.
- Cache frequent queries with short TTL via Upstash.
- Ensure v6 UIMessage.parts alignment for returned context and references.

## Consequences

- Improved relevance and maintainability; single Next backend.
- Adds provider dependency; must handle fallback if rerank unavailable.

## References

- v6 Reranking: <https://v6.ai-sdk.dev/docs/ai-sdk-core/reranking>
- Embeddings: <https://v6.ai-sdk.dev/docs/ai-sdk-core/embeddings>
- Next.js App Router: <https://v6.ai-sdk.dev/docs/getting-started/nextjs-app-router>
