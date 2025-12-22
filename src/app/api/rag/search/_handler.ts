/**
 * @fileoverview Pure handler for RAG search requests.
 */

import "server-only";

import type { RagSearchRequest } from "@schemas/rag";
import { NextResponse } from "next/server";
import { createReranker } from "@/lib/rag/reranker";
import { retrieveDocuments } from "@/lib/rag/retriever";
import type { TypedServerSupabase } from "@/lib/supabase/server";

export interface RagSearchDeps {
  supabase: TypedServerSupabase;
}

export async function handleRagSearch(
  deps: RagSearchDeps,
  body: RagSearchRequest
): Promise<Response> {
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
    supabase: deps.supabase,
  });

  return NextResponse.json(result);
}
