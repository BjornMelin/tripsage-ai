/**
 * @fileoverview Server-only RAG retrieval (hybrid/semantic) and optional reranking.
 */

import "server-only";

import { openai } from "@ai-sdk/openai";
import type { RagSearchResponse, RagSearchResult, RetrieverConfig } from "@schemas/rag";
import { retrieverConfigSchema } from "@schemas/rag";
import type { SupabaseClient } from "@supabase/supabase-js";
import { embed } from "ai";
import type { Database } from "@/lib/supabase/database.types";
import { createServerLogger } from "@/lib/telemetry/logger";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import { toPgvector } from "./pgvector";
import { createReranker, type Reranker } from "./reranker";

const logger = createServerLogger("rag.retriever");

/**
 * Retrieve parameters for the core retrieval function.
 */
export interface RetrieveDocumentsParams {
  /** Search query. */
  query: string;
  /** Supabase client instance. */
  supabase: SupabaseClient<Database>;
  /** Retriever configuration. */
  config?: Partial<RetrieverConfig>;
  /** Custom reranker instance. */
  reranker?: Reranker;
}

/**
 * Retrieve documents using hybrid search with optional reranking.
 *
 * Process:
 * 1. Generate query embedding via embed()
 * 2. Execute hybrid_rag_search RPC (vector + lexical)
 * 3. Optionally rerank results via Together.ai
 * 4. Return scored results with latency tracking
 *
 * @param params - Retrieval parameters.
 * @returns Search results with scores and metadata.
 *
 * @example
 * ```typescript
 * const result = await retrieveDocuments({
 *   query: "best hotels in Paris",
 *   supabase,
 *   config: { namespace: "accommodations", limit: 10 }
 * });
 * ```
 */
// biome-ignore lint/suspicious/useAwait: Returns withTelemetrySpan promise which is async
export async function retrieveDocuments(
  params: RetrieveDocumentsParams
): Promise<RagSearchResponse> {
  const { query, supabase, reranker: customReranker } = params;
  const config = retrieverConfigSchema.parse(params.config ?? {});

  const startTime = performance.now();

  return withTelemetrySpan(
    "rag.retriever.retrieve_documents",
    {
      attributes: {
        "rag.retriever.keyword_weight": config.keywordWeight,
        "rag.retriever.limit": config.limit,
        "rag.retriever.namespace": config.namespace ?? "all",
        "rag.retriever.semantic_weight": config.semanticWeight,
        "rag.retriever.threshold": config.threshold,
        "rag.retriever.use_reranking": config.useReranking,
      },
    },
    async () => {
      // Generate query embedding
      const { embedding } = await embed({
        model: openai.embeddingModel("text-embedding-3-small"),
        value: query,
      });

      if (embedding.length !== 1536) {
        throw new Error(
          `Query embedding dimension mismatch: expected 1536, got ${embedding.length}`
        );
      }

      // Execute hybrid search RPC
      const { data, error } = await supabase.rpc("hybrid_rag_search", {
        // biome-ignore lint/style/useNamingConvention: RPC parameter name
        filter_namespace: config.namespace,
        // biome-ignore lint/style/useNamingConvention: RPC parameter name
        keyword_weight: config.keywordWeight,
        // biome-ignore lint/style/useNamingConvention: RPC parameter name
        match_count: config.useReranking ? config.limit * 2 : config.limit,
        // biome-ignore lint/style/useNamingConvention: RPC parameter name
        match_threshold: config.threshold,
        // biome-ignore lint/style/useNamingConvention: RPC parameter name
        query_embedding: toPgvector(embedding),
        // biome-ignore lint/style/useNamingConvention: RPC parameter name
        query_text: query,
        // biome-ignore lint/style/useNamingConvention: RPC parameter name
        semantic_weight: config.semanticWeight,
      });

      if (error) {
        throw new Error(`Hybrid search failed: ${error.message}`);
      }

      // Map RPC results to search result schema
      const results: RagSearchResult[] = (data ?? []).map((row) => ({
        chunkIndex: row.chunk_index ?? 0,
        combinedScore: row.combined_score ?? 0,
        content: row.content ?? "",
        id: row.id ?? "",
        keywordRank: row.keyword_rank ?? 0,
        metadata: (row.metadata ?? {}) as Record<string, unknown>,
        namespace: (row.namespace ?? "default") as RagSearchResult["namespace"],
        similarity: row.similarity ?? 0,
        sourceId: row.source_id ?? null,
      }));

      // Apply reranking if enabled and we have results
      let finalResults: RagSearchResult[];
      let rerankingApplied = false;

      if (config.useReranking && results.length > 0) {
        const reranker =
          customReranker ?? createReranker({ provider: "together", timeout: 700 });

        try {
          finalResults = await reranker.rerank(query, results, config.limit);
          rerankingApplied = true;
        } catch (error) {
          // Graceful fallback: use original results
          logger.warn("reranking_fallback", {
            error: error instanceof Error ? error.message : "unknown_error",
            resultCount: results.length,
          });
          finalResults = results.slice(0, config.limit);
        }
      } else {
        // No reranking: just limit results
        finalResults = results.slice(0, config.limit);
      }

      const latencyMs = performance.now() - startTime;

      const response: RagSearchResponse = {
        latencyMs: Math.round(latencyMs),
        query,
        rerankingApplied,
        results: finalResults,
        success: true,
        total: finalResults.length,
      };

      logger.info("retrieve_complete", {
        latencyMs: Math.round(latencyMs),
        namespace: config.namespace,
        rerankingApplied,
        resultCount: finalResults.length,
      });

      return response;
    }
  );
}

/**
 * Simple semantic search without hybrid or reranking.
 *
 * For cases where pure vector similarity is sufficient.
 *
 * @param params - Search parameters.
 * @returns Search results.
 */
export async function semanticSearch(params: {
  query: string;
  supabase: SupabaseClient<Database>;
  namespace?: string;
  limit?: number;
  threshold?: number;
}): Promise<RagSearchResult[]> {
  const { query, supabase, namespace, limit = 10, threshold = 0.7 } = params;

  // Generate query embedding
  const { embedding } = await embed({
    model: openai.embeddingModel("text-embedding-3-small"),
    value: query,
  });

  if (embedding.length !== 1536) {
    throw new Error(
      `Query embedding dimension mismatch: expected 1536, got ${embedding.length}`
    );
  }

  // Call simpler match function
  const { data, error } = await supabase.rpc("match_rag_documents", {
    // biome-ignore lint/style/useNamingConvention: RPC parameter name
    filter_namespace: namespace,
    // biome-ignore lint/style/useNamingConvention: RPC parameter name
    match_count: limit,
    // biome-ignore lint/style/useNamingConvention: RPC parameter name
    match_threshold: threshold,
    // biome-ignore lint/style/useNamingConvention: RPC parameter name
    query_embedding: toPgvector(embedding),
  });

  if (error) {
    throw new Error(`Semantic search failed: ${error.message}`);
  }

  return (data ?? []).map((row) => ({
    chunkIndex: row.chunk_index ?? 0,
    combinedScore: row.similarity ?? 0,
    content: row.content ?? "",
    id: row.id ?? "",
    keywordRank: 0,
    metadata: (row.metadata ?? {}) as Record<string, unknown>,
    namespace: (row.namespace ?? "default") as RagSearchResult["namespace"],
    similarity: row.similarity ?? 0,
    sourceId: row.source_id ?? null,
  }));
}
