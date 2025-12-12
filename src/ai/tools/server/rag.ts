/**
 * @fileoverview RAG search tool for AI agents (server-only).
 *
 * Provides semantic search with hybrid scoring and reranking
 * for knowledge base queries.
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import { TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import { ragSearchInputSchema } from "@schemas/rag";
import { hashInputForCache } from "@/lib/cache/hash";
import { createReranker } from "@/lib/rag/reranker";
import { retrieveDocuments } from "@/lib/rag/retriever";
import { createServerSupabase } from "@/lib/supabase/server";

/**
 * RAG search tool for knowledge base queries.
 *
 * Combines vector similarity, lexical search, and cross-encoder reranking
 * to retrieve relevant documents from the knowledge base.
 *
 * @param query - Natural language search query.
 * @param namespace - Optional document namespace to filter.
 * @param limit - Maximum results to return (1-20, default 5).
 * @param threshold - Minimum similarity threshold (0-1, default 0.7).
 * @returns Matching documents with content and relevance scores.
 *
 * @example
 * ```typescript
 * const results = await ragSearch.execute({
 *   query: "best hotels in Paris with pool",
 *   namespace: "accommodations",
 *   limit: 5
 * });
 * ```
 */
export const ragSearch = createAiTool({
  description:
    "Search the knowledge base using RAG (hybrid vector + keyword search with reranking). " +
    "Returns relevant document chunks with similarity scores. " +
    "Use for finding travel guides, accommodation info, destination details, and activity recommendations.",
  execute: async ({ query, namespace, limit, threshold }) => {
    const supabase = await createServerSupabase();

    // Create reranker with Together.ai/Mixedbread
    const reranker = createReranker({
      provider: "together",
      timeout: 700,
    });

    const result = await retrieveDocuments({
      config: {
        limit,
        namespace,
        threshold,
        useReranking: true,
      },
      query,
      reranker,
      supabase,
    });

    // Return simplified results for the agent
    return {
      latencyMs: result.latencyMs,
      results: result.results.map((r) => ({
        chunkIndex: r.chunkIndex,
        content: r.content,
        metadata: r.metadata,
        namespace: r.namespace,
        score: r.rerankScore ?? r.combinedScore,
        sourceId: r.sourceId,
      })),
      total: result.total,
    };
  },
  guardrails: {
    cache: {
      key: (p) => {
        const namespacePart = p.namespace ?? "all";
        const queryPart = p.query.length > 64 ? hashInputForCache(p.query) : p.query;
        return `rag:${namespacePart}:${queryPart}`;
      },
      ttlSeconds: 300, // 5 minute cache
    },
    rateLimit: {
      errorCode: TOOL_ERROR_CODES.toolRateLimited,
      limit: 30,
      window: "1 m",
    },
  },
  inputSchema: ragSearchInputSchema,
  name: "ragSearch",
});
