/**
 * @fileoverview RAG document indexing endpoint.
 *
 * Batch indexes documents with chunking and embedding generation.
 * POST /api/rag/index
 */

import "server-only";

import { ragIndexRequestSchema } from "@schemas/rag";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { indexDocuments } from "@/lib/rag/indexer";

/**
 * POST /api/rag/index
 *
 * Index documents into the RAG store with automatic chunking and embedding.
 *
 * @param req - Request with documents array.
 * @returns Index result with counts and failed documents. Always returns HTTP 200;
 *          partial success is conveyed via `success: false` and per-item failures.
 *
 * @example
 * ```bash
 * curl -X POST /api/rag/index \
 *   -H "Content-Type: application/json" \
 *   -d '{
 *     "documents": [{ "content": "Travel guide..." }],
 *     "namespace": "travel_tips",
 *     "chunkSize": 512
 *   }'
 * ```
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "rag:index",
  schema: ragIndexRequestSchema,
  telemetry: "rag.index",
})(async (_req: NextRequest, { supabase }, body) => {
  const result = await indexDocuments({
    config: {
      chunkOverlap: body.chunkOverlap,
      chunkSize: body.chunkSize,
      namespace: body.namespace,
    },
    documents: body.documents,
    supabase,
  });

  return NextResponse.json(result, { status: 200 });
});
