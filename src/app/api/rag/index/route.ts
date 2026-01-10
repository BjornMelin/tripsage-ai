/**
 * @fileoverview RAG document indexing endpoint.
 */

import "server-only";

import { ragIndexRequestSchema } from "@schemas/rag";
import type { NextRequest } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { requireUserId } from "@/lib/api/route-helpers";
import { handleRagIndex } from "./_handler";

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
  botId: true,
  rateLimit: "rag:index",
  schema: ragIndexRequestSchema,
  telemetry: "rag.index",
})((_req: NextRequest, { supabase, user }, body) => {
  const userResult = requireUserId(user);
  if (!userResult.ok) return userResult.error;

  return handleRagIndex({ supabase, userId: userResult.data }, body);
});
