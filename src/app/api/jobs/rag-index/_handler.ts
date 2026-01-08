/**
 * @fileoverview Pure handler for RAG indexing jobs.
 */

import "server-only";

import type { RagIndexResponse } from "@schemas/rag";
import type { RagIndexJob } from "@schemas/webhooks";
import { indexDocuments } from "@/lib/rag/indexer";
import type { TypedAdminSupabase } from "@/lib/supabase/admin";

export interface RagIndexJobDeps {
  supabase: TypedAdminSupabase;
}

export async function handleRagIndexJob(
  deps: RagIndexJobDeps,
  job: RagIndexJob
): Promise<RagIndexResponse> {
  return await indexDocuments({
    chatId: job.chatId ?? undefined,
    config: {
      chunkOverlap: job.chunkOverlap,
      chunkSize: job.chunkSize,
      namespace: job.namespace,
    },
    documents: job.documents,
    supabase: deps.supabase,
    tripId: job.tripId ?? undefined,
    userId: job.userId,
  });
}
