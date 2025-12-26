/**
 * @fileoverview RAG document search endpoint.
 */

import "server-only";

import { ragSearchRequestSchema } from "@schemas/rag";
import type { NextRequest } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { handleRagSearch } from "./_handler";

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
})(async (_req: NextRequest, { supabase }, body) =>
  handleRagSearch({ supabase }, body)
);
