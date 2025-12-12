/**
 * @fileoverview RAG document search endpoint.
 *
 * Hybrid search with vector similarity, lexical matching, and reranking.
 * POST /api/rag/search
 */

import "server-only";

import { ragSearchRequestSchema } from "@schemas/rag";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { createReranker } from "@/lib/rag/reranker";
import { retrieveDocuments } from "@/lib/rag/retriever";

/**
 * POST /api/rag/search
 *
 * Search documents using hybrid search with optional reranking.
 *
 * @param req - Request with search query and options.
 * @returns Search results with scores and metadata.
 *
 * @example
 * ```bash
 * curl -X POST /api/rag/search \
 *   -H "Content-Type: application/json" \
 *   -d '{
 *     "query": "best hotels in Paris",
 *     "namespace": "accommodations",
 *     "limit": 10,
 *     "useReranking": true
 *   }'
 * ```
 */
export const POST = withApiGuards({
  auth: true, // Authentication required for search
  rateLimit: "rag:search",
  schema: ragSearchRequestSchema,
  telemetry: "rag.search",
})(async (_req: NextRequest, { supabase }, body) => {
  const reranker = body.useReranking
    ? createReranker({ provider: "together", timeout: 700 })
    : createReranker({ provider: "noop" });

  const result = await retrieveDocuments({
    config: {
      keywordWeight: body.keywordWeight,
      limit: body.limit,
      namespace: body.namespace,
      semanticWeight: body.semanticWeight,
      threshold: body.threshold,
      useReranking: body.useReranking,
    },
    query: body.query,
    reranker,
    supabase,
  });

  return NextResponse.json(result);
});
