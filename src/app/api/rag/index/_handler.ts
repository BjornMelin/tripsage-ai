/**
 * @fileoverview Pure handler for RAG indexing requests.
 */

import "server-only";

import type { RagIndexRequest } from "@schemas/rag";
import { NextResponse } from "next/server";
import { indexDocuments } from "@/lib/rag/indexer";
import type { TypedServerSupabase } from "@/lib/supabase/server";

export interface RagIndexDeps {
  supabase: TypedServerSupabase;
}

export async function handleRagIndex(
  deps: RagIndexDeps,
  body: RagIndexRequest
): Promise<Response> {
  const result = await indexDocuments({
    config: {
      chunkOverlap: body.chunkOverlap,
      chunkSize: body.chunkSize,
      namespace: body.namespace,
    },
    documents: body.documents,
    supabase: deps.supabase,
  });

  return NextResponse.json(result, { status: 200 });
}
