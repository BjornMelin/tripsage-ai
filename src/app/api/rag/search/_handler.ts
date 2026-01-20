/**
 * @fileoverview Pure handler for RAG search requests.
 */

import "server-only";

import type { RagNamespace, RagSearchRequest } from "@schemas/rag";
import { ragNamespaceSchema } from "@schemas/rag";
import { NextResponse } from "next/server";
import { getTextEmbeddingModelId } from "@/lib/ai/embeddings/text-embedding-model";
import { hashInputForCache } from "@/lib/cache/hash";
import { getCachedJsonSafe, setCachedJson } from "@/lib/cache/upstash";
import { createReranker } from "@/lib/rag/reranker";
import { retrieveDocuments } from "@/lib/rag/retriever";
import { hashIdentifier } from "@/lib/ratelimit/identifier";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";
import { recordTelemetryEvent } from "@/lib/telemetry/span";

/**
 * Dependencies required for the RAG search handler.
 */
export interface RagSearchDeps {
  /** Authenticated Supabase client. */
  supabase: TypedServerSupabase;
  /** Authenticated user ID. */
  userId: string;
}

const logger = createServerLogger("rag.search");
const RAG_SEARCH_CACHE_TTL_SECONDS = 120;

/**
 * Result structure for a cached RAG search item.
 */
type CachedRagSearchResult = {
  id: string;
  chunkIndex: number;
  combinedScore: number;
  keywordRank: number;
  similarity: number;
  rerankScore?: number;
};

/**
 * Top-level cache entry for RAG search results.
 */
type CachedRagSearchEntry = {
  rerankingApplied: boolean;
  results: CachedRagSearchResult[];
  total: number;
  version: 1;
};

/**
 * Creates a deterministic cache key for a RAG search request.
 *
 * @param userId - ID of the user performing the search.
 * @param body - The search request parameters.
 * @returns A unique cache key string.
 */
function createRagSearchCacheKey(userId: string, body: RagSearchRequest): string {
  const userHash = hashIdentifier(userId);
  const embeddingModelId = getTextEmbeddingModelId();

  const payload = {
    embeddingModelId,
    keywordWeight: body.keywordWeight,
    limit: body.limit,
    namespace: body.namespace ?? null,
    query: body.query,
    semanticWeight: body.semanticWeight,
    threshold: body.threshold,
    useReranking: body.useReranking,
  };

  return `rag_search:v1:${userHash}:${hashInputForCache(payload)}`;
}

/**
 * Validates and normalizes a RAG namespace string.
 *
 * @param value - The raw namespace value to validate.
 * @returns A valid RagNamespace, defaulting to "default" if invalid.
 */
function validateNamespace(value: unknown): RagNamespace {
  const result = ragNamespaceSchema.safeParse(value);
  return result.success ? result.data : "default";
}

/**
 * Handles RAG search requests with multi-stage caching and rehydration.
 *
 * The handler attempts to serve results from Upstash Redis. If a cache hit occurs,
 * it rehydrates document content and metadata from Supabase to ensure fresh data.
 * If a cache miss occurs, it performs a hybrid search, applies optional reranking,
 * and populates the cache.
 *
 * @param deps - Injected dependencies (Supabase client, user ID).
 * @param body - Validated RAG search request parameters.
 * @returns A JSON response containing search results and metadata.
 */
export async function handleRagSearch(
  deps: RagSearchDeps,
  body: RagSearchRequest
): Promise<Response> {
  const cacheKey = createRagSearchCacheKey(deps.userId, body);

  const cached = await getCachedJsonSafe<CachedRagSearchEntry>(cacheKey);
  if (cached.status === "hit") {
    if (cached.data.results.length === 0) {
      return NextResponse.json({
        latencyMs: 0,
        query: body.query,
        rerankingApplied: cached.data.rerankingApplied,
        results: [],
        success: true,
        total: cached.data.total,
      });
    }

    const wantPairs = cached.data.results.map((r) => ({
      chunkIndex: r.chunkIndex,
      id: r.id,
    }));
    const uniqueIds = Array.from(new Set(wantPairs.map((p) => p.id)));
    const wantKeySet = new Set(wantPairs.map((p) => `${p.id}:${p.chunkIndex}`));

    const { data, error } = await deps.supabase
      .from("rag_documents")
      .select("id, chunk_index, content, metadata, namespace, source_id")
      .in("id", uniqueIds);

    if (error) {
      recordTelemetryEvent("rag.cache.rehydration_db_error", {
        attributes: {
          errorMessage: error.message,
          uniqueIdCount: uniqueIds.length,
        },
        level: "warning",
      });
    } else if (data && data.length > 0) {
      const rowByKey = new Map<string, (typeof data)[number]>();
      for (const row of data) {
        const key = `${row.id}:${row.chunk_index ?? 0}`;
        if (!wantKeySet.has(key)) continue;
        rowByKey.set(key, row);
      }

      const rehydrated = cached.data.results
        .map((result) => {
          const key = `${result.id}:${result.chunkIndex}`;
          const row = rowByKey.get(key);
          if (!row) return null;
          return {
            ...result,
            content: row.content ?? "",
            metadata: (row.metadata ?? {}) as Record<string, unknown>,
            namespace: validateNamespace(row.namespace ?? "default"),
            sourceId: row.source_id ?? null,
          };
        })
        .filter((row): row is NonNullable<typeof row> => row !== null);

      if (rehydrated.length === cached.data.results.length) {
        return NextResponse.json({
          latencyMs: 0,
          query: body.query,
          rerankingApplied: cached.data.rerankingApplied,
          results: rehydrated,
          success: true,
          total: cached.data.total,
        });
      }

      const missingKeys = Array.from(wantKeySet).filter((key) => !rowByKey.has(key));
      recordTelemetryEvent("rag.cache.partial_rehydration", {
        attributes: {
          cachedCount: cached.data.results.length,
          missingKeys: missingKeys.join(","),
          queryLength: body.query.length,
          rehydratedCount: rehydrated.length,
          rerankingApplied: cached.data.rerankingApplied,
        },
        level: "warning",
      });
    }
  }

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

  const cacheEntry: CachedRagSearchEntry = {
    rerankingApplied: result.rerankingApplied,
    results: result.results.map((row) => ({
      chunkIndex: row.chunkIndex,
      combinedScore: row.combinedScore,
      id: row.id,
      keywordRank: row.keywordRank,
      rerankScore: row.rerankScore,
      similarity: row.similarity,
    })),
    total: result.total,
    version: 1,
  };
  try {
    await setCachedJson(cacheKey, cacheEntry, RAG_SEARCH_CACHE_TTL_SECONDS);
  } catch (error) {
    logger.warn("RAG search cache write failed", {
      cacheKey,
      error,
      total: cacheEntry.total,
      version: cacheEntry.version,
    });
  }

  return NextResponse.json(result);
}
