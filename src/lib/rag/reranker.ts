/**
 * @fileoverview Pluggable reranker interface with Together.ai implementation.
 *
 * Provides cross-encoder reranking to improve RAG result relevance.
 * Primary: Together.ai with Mixedbread mxbai-rerank-large-v2
 * Fallback: NoOp reranker returns documents unchanged
 */

import "server-only";

import { togetherai } from "@ai-sdk/togetherai";
import type { RagSearchResult, RerankerConfig } from "@schemas/rag";
import { rerankerConfigSchema } from "@schemas/rag";
import { rerank } from "ai";
import { createServerLogger } from "@/lib/telemetry/logger";
import { withTelemetrySpan } from "@/lib/telemetry/span";

const logger = createServerLogger("rag.reranker");

/**
 * Pluggable reranker interface.
 * Implementations must rerank documents and return scores.
 */
export interface Reranker {
  /**
   * Reranks documents by relevance to the query.
   *
   * @param query - User's search query.
   * @param documents - Retrieved documents to rerank.
   * @param topN - Number of top results to return.
   * @returns Reranked results with relevance scores.
   */
  rerank(
    query: string,
    documents: RagSearchResult[],
    topN: number
  ): Promise<RagSearchResult[]>;
}

/**
 * Together.ai reranker using Mixedbread mxbai-rerank-large-v2.
 *
 * Features:
 * - 100x cheaper than Cohere ($0.002/1k vs $0.05/1k queries)
 * - Native AI SDK v6 support via @ai-sdk/togetherai
 * - 100+ languages, 8K context, code/SQL support
 * - ELO 1468 quality (competitive for RAG)
 */
export class TogetherReranker implements Reranker {
  private readonly config: RerankerConfig;

  constructor(config: Partial<RerankerConfig> = {}) {
    this.config = rerankerConfigSchema.parse({ ...config, provider: "together" });
  }

  // biome-ignore lint/suspicious/useAwait: Returns withTelemetrySpan promise which is async
  async rerank(
    query: string,
    documents: RagSearchResult[],
    topN: number
  ): Promise<RagSearchResult[]> {
    if (documents.length === 0) {
      return [];
    }

    const effectiveTopN = Math.min(topN, documents.length, this.config.topN);

    return withTelemetrySpan(
      "rag.reranker.together",
      {
        attributes: {
          "rag.reranker.document_count": documents.length,
          "rag.reranker.provider": "together",
          "rag.reranker.top_n": effectiveTopN,
        },
      },
      async () => {
        try {
          const { ranking } = await rerank({
            abortSignal: AbortSignal.timeout(this.config.timeout),
            documents: documents.map((d) => d.content),
            maxRetries: this.config.maxRetries,
            model: togetherai.reranking("mixedbread-ai/Mxbai-Rerank-Large-V2"),
            query,
            topN: effectiveTopN,
          });

          // Map reranked results back to original documents with scores
          const rerankedDocs: RagSearchResult[] = ranking.map((result) => ({
            ...documents[result.originalIndex],
            rerankScore: result.score,
          }));

          // Sort by rerank score (already sorted by rerank(), but ensure order)
          rerankedDocs.sort((a, b) => (b.rerankScore ?? 0) - (a.rerankScore ?? 0));

          logger.info("rerank_success", {
            inputCount: documents.length,
            outputCount: rerankedDocs.length,
            topN: effectiveTopN,
          });

          return rerankedDocs;
        } catch (error) {
          // Log error but don't throw - allow graceful fallback
          logger.error("rerank_failed", {
            error: error instanceof Error ? error.message : "unknown_error",
            inputCount: documents.length,
          });

          // Fallback: return original documents sorted by combined score
          return documents
            .slice(0, effectiveTopN)
            .sort((a, b) => b.combinedScore - a.combinedScore);
        }
      }
    );
  }
}

/**
 * NoOp reranker that returns documents unchanged.
 * Used as fallback when reranking is disabled or fails.
 */
export class NoOpReranker implements Reranker {
  // biome-ignore lint/suspicious/useAwait: Interface requires async signature
  async rerank(
    _query: string,
    documents: RagSearchResult[],
    topN: number
  ): Promise<RagSearchResult[]> {
    // Return documents sorted by combined score, limited to topN
    return documents
      .slice(0, Math.min(topN, documents.length))
      .sort((a, b) => b.combinedScore - a.combinedScore);
  }
}

/**
 * Factory function to create a reranker instance.
 *
 * @param config - Reranker configuration.
 * @returns Configured reranker instance.
 *
 * @example
 * ```typescript
 * const reranker = createReranker({ provider: "together", timeout: 700 });
 * const reranked = await reranker.rerank(query, documents, 10);
 * ```
 */
export function createReranker(config: Partial<RerankerConfig> = {}): Reranker {
  const parsedConfig = rerankerConfigSchema.parse(config);

  switch (parsedConfig.provider) {
    case "together":
      return new TogetherReranker(parsedConfig);
    case "noop":
      return new NoOpReranker();
    default: {
      // TypeScript exhaustiveness check
      const _exhaustive: never = parsedConfig.provider;
      throw new Error(`Unknown reranker provider: ${_exhaustive}`);
    }
  }
}
