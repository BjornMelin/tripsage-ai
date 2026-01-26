/**
 * @fileoverview Server-only RAG indexing (chunking + embeddings + storage).
 */

import "server-only";

import type {
  IndexerConfig,
  RagDocument,
  RagIndexFailedDoc,
  RagIndexResponse,
  RagNamespace,
} from "@schemas/rag";
import { indexerConfigSchema } from "@schemas/rag";
import type { SupabaseClient } from "@supabase/supabase-js";
import { embedMany } from "ai";
import {
  getTextEmbeddingModel,
  TEXT_EMBEDDING_DIMENSIONS,
} from "@/lib/ai/embeddings/text-embedding-model";
import { secureUuid } from "@/lib/security/random";
import type { Database } from "@/lib/supabase/database.types";
import { deleteMany, upsertMany } from "@/lib/supabase/typed-helpers";
import { createServerLogger } from "@/lib/telemetry/logger";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import { RagLimitError } from "./errors";
import { toPgvector } from "./pgvector";

const logger = createServerLogger("rag.indexer");
const EMBED_TIMEOUT_BASE_MS = 30_000;
const EMBED_TIMEOUT_PER_CHUNK_MS = 100;

/** Token to character ratio approximation (conservative). */
const CHARS_PER_TOKEN = 4;
/** Max chunks per embedding batch to prevent runaway costs and respect API limits. */
const MAX_CHUNKS_PER_EMBED_BATCH = 1200;

/**
 * Computes a dynamic timeout for embedding requests based on chunk count and parallelism.
 *
 * @param chunkCount - Number of chunks being embedded.
 * @param maxParallelCalls - Configured maximum parallel model calls.
 * @returns Timeout duration in milliseconds.
 */
function getEmbedTimeoutMs(chunkCount: number, maxParallelCalls: number): number {
  const parallelCalls = Math.max(1, maxParallelCalls);
  const rounds = Math.ceil(chunkCount / parallelCalls);
  return Math.max(EMBED_TIMEOUT_BASE_MS, rounds * EMBED_TIMEOUT_PER_CHUNK_MS);
}

/**
 * Contextual data for chunk limit enforcement logs and errors.
 */
interface ChunkLimitContext {
  batchStartIndex: number;
  chunkOverlap: number;
  chunkSize: number;
  documentCount: number;
}

/**
 * Enforces the maximum number of chunks allowed per embedding batch to prevent runaway costs.
 *
 * @param count - Actual number of chunks to be processed.
 * @param context - Metadata for logging and error reporting.
 * @throws {RagLimitError} If the chunk count exceeds MAX_CHUNKS_PER_EMBED_BATCH.
 */
function enforceChunkLimit(count: number, context: ChunkLimitContext): void {
  if (count <= MAX_CHUNKS_PER_EMBED_BATCH) return;
  logger.warn("chunk_limit_exceeded", {
    ...context,
    chunkCount: count,
    limit: MAX_CHUNKS_PER_EMBED_BATCH,
  });
  // Hard limit to avoid runaway embedding costs; callers should split batches.
  throw new RagLimitError("too_many_chunks", {
    chunkCount: count,
    limit: MAX_CHUNKS_PER_EMBED_BATCH,
  });
}

/**
 * Validates that all generated embeddings match the expected vector dimensionality.
 *
 * @param embeddings - List of embedding vectors to validate.
 * @param expectedDim - Required number of dimensions (e.g., 1536).
 * @param context - Optional description for error reporting.
 * @throws {Error} If any embedding has an incorrect dimension count.
 */
function assertEmbeddingDimensions(
  embeddings: readonly number[][],
  expectedDim: number,
  context?: string
): void {
  for (let i = 0; i < embeddings.length; i += 1) {
    const embedding = embeddings[i];
    if (!embedding || embedding.length !== expectedDim) {
      const contextSuffix = context ? ` (${context})` : "";
      throw new Error(
        `Embedding dimension mismatch${contextSuffix} at index ${i}: expected ${expectedDim}, got ${embedding?.length ?? -1}`
      );
    }
  }
}

/**
 * Chunk document text with overlap.
 *
 * Uses character-based chunking with configurable size and overlap.
 * Attempts to break at sentence boundaries when possible.
 *
 * @param text - Document text to chunk.
 * @param chunkSize - Target chunk size in tokens (converted to chars).
 * @param chunkOverlap - Overlap between chunks in tokens.
 * @returns Array of text chunks.
 */
export function chunkText(
  text: string,
  chunkSize: number = 512,
  chunkOverlap: number = 100
): string[] {
  const chunkChars = chunkSize * CHARS_PER_TOKEN;
  const overlapChars = chunkOverlap * CHARS_PER_TOKEN;

  if (text.length <= chunkChars) {
    return [text.trim()].filter((t) => t.length > 0);
  }

  const chunks: string[] = [];
  let start = 0;

  while (start < text.length) {
    let end = Math.min(start + chunkChars, text.length);

    // Try to break at sentence boundary if not at end
    if (end < text.length) {
      const searchStart = Math.max(start + chunkChars - 200, start);
      const searchEnd = Math.min(start + chunkChars + 100, text.length);
      const searchText = text.slice(searchStart, searchEnd);

      // Find last sentence boundary in search window
      const sentenceBreaks = [". ", "! ", "? ", ".\n", "!\n", "?\n"];
      let bestBreak = -1;

      for (const br of sentenceBreaks) {
        const idx = searchText.lastIndexOf(br);
        if (idx !== -1) {
          const absoluteIdx = searchStart + idx + br.length;
          if (absoluteIdx > start && absoluteIdx <= start + chunkChars + 50) {
            if (bestBreak === -1 || absoluteIdx > bestBreak) {
              bestBreak = absoluteIdx;
            }
          }
        }
      }

      if (bestBreak !== -1) {
        end = bestBreak;
      }
    }

    const chunk = text.slice(start, end).trim();
    if (chunk.length > 0) {
      chunks.push(chunk);
    }

    // Move start forward with overlap
    // Ensure start always advances to prevent infinite loop
    const newStart = end - overlapChars;
    if (newStart <= start) {
      // If overlap would cause us to go backwards or stay in place, just advance to end
      start = end;
    } else {
      start = newStart;
    }
    if (start >= text.length) break;
  }

  return chunks;
}

/**
 * Index parameters for the core indexing function.
 */
export interface IndexDocumentsParams {
  /** Documents to index. */
  documents: RagDocument[];
  /** Supabase client instance. */
  supabase: SupabaseClient<Database>;
  /** Authenticated user id (used for RLS-scoped writes). */
  userId: string;
  /** Optional trip scope for all indexed chunks. */
  tripId?: number | null;
  /** Optional chat session scope for all indexed chunks. */
  chatId?: string | null;
  /** Indexer configuration. */
  config?: Partial<IndexerConfig>;
}

/**
 * Index documents into the RAG store.
 *
 * Process:
 * 1. Chunk each document based on config
 * 2. Generate embeddings in batches via embedMany()
 * 3. Upsert chunks to rag_documents table
 * 4. Track failures per document
 *
 * @param params - Indexing parameters.
 * @returns Index operation result with counts and failures.
 *
 * @example
 * ```typescript
 * const result = await indexDocuments({
 *   documents: [{ content: "Travel guide…", metadata: { type: "guide" } }],
 *   supabase,
 *   config: { namespace: "travel_tips", chunkSize: 512 }
 * });
 * ```
 */
// biome-ignore lint/suspicious/useAwait: Returns withTelemetrySpan promise which is async
export async function indexDocuments(
  params: IndexDocumentsParams
): Promise<RagIndexResponse> {
  const { chatId, documents, supabase, tripId, userId } = params;
  const config = indexerConfigSchema.parse(params.config ?? {});

  return withTelemetrySpan(
    "rag.indexer.index_documents",
    {
      attributes: {
        "rag.indexer.batch_size": config.batchSize,
        "rag.indexer.chat_id_present": Boolean(chatId),
        "rag.indexer.chunk_overlap": config.chunkOverlap,
        "rag.indexer.chunk_size": config.chunkSize,
        "rag.indexer.document_count": documents.length,
        "rag.indexer.max_parallel_calls": config.maxParallelCalls,
        "rag.indexer.namespace": config.namespace,
        "rag.indexer.trip_id_present": Boolean(tripId),
      },
    },
    async () => {
      const failed: RagIndexFailedDoc[] = [];
      let indexedCount = 0;
      let chunksCreated = 0;

      // Process documents in batches to control memory
      for (let i = 0; i < documents.length; i += config.batchSize) {
        const batch = documents.slice(i, i + config.batchSize);

        try {
          const batchResult = await indexBatch({
            batch,
            batchStartIndex: i,
            chatId,
            config,
            supabase,
            tripId,
            userId,
          });

          indexedCount += batchResult.indexed;
          chunksCreated += batchResult.chunksCreated;
          failed.push(...batchResult.failed);
        } catch (error) {
          // If entire batch fails, mark all documents in batch as failed
          logger.error("batch_failed", {
            batchStart: i,
            error: error instanceof Error ? error.message : "unknown_error",
          });

          for (let j = 0; j < batch.length; j++) {
            failed.push({
              error: error instanceof Error ? error.message : "batch_failed",
              index: i + j,
            });
          }
        }
      }

      const result: RagIndexResponse = {
        chunksCreated,
        failed,
        indexed: indexedCount,
        namespace: config.namespace,
        success: failed.length === 0,
        total: documents.length,
      };

      logger.info("index_complete", {
        chunksCreated,
        failedCount: failed.length,
        indexedCount,
        namespace: config.namespace,
        total: documents.length,
      });

      return result;
    }
  );
}

/**
 * Parameters for internal batch processing of documents.
 */
interface IndexBatchParams {
  batch: RagDocument[];
  batchStartIndex: number;
  chatId?: string | null;
  config: IndexerConfig;
  supabase: SupabaseClient<Database>;
  tripId?: number | null;
  userId: string;
}

/**
 * Result of a single batch indexing operation.
 */
interface IndexBatchResult {
  chunksCreated: number;
  failed: RagIndexFailedDoc[];
  indexed: number;
}

/**
 * Index a batch of documents.
 *
 * @internal
 */
async function indexBatch(params: IndexBatchParams): Promise<IndexBatchResult> {
  const { batch, batchStartIndex, chatId, config, supabase, tripId, userId } = params;

  const failed: RagIndexFailedDoc[] = [];
  let indexed = 0;
  let chunksCreated = 0;
  const estimatedChunkChars = Math.max(
    1,
    (config.chunkSize - config.chunkOverlap) * CHARS_PER_TOKEN
  );
  let estimatedChunkCount = 0;

  // Prepare all chunks with document index tracking
  const allChunks: Array<{
    chunk: string;
    chunkIndex: number;
    docIndex: number;
    document: RagDocument;
    documentId: string;
  }> = [];

  for (let docIdx = 0; docIdx < batch.length; docIdx++) {
    const document = batch[docIdx];

    if (!document.content || document.content.trim().length === 0) {
      failed.push({
        error: "empty_content",
        index: batchStartIndex + docIdx,
      });
      continue;
    }

    const documentId = document.id ?? secureUuid();
    estimatedChunkCount += Math.ceil(document.content.length / estimatedChunkChars);
    enforceChunkLimit(estimatedChunkCount, {
      batchStartIndex,
      chunkOverlap: config.chunkOverlap,
      chunkSize: config.chunkSize,
      documentCount: batch.length,
    });
    const chunks = chunkText(document.content, config.chunkSize, config.chunkOverlap);

    for (let chunkIdx = 0; chunkIdx < chunks.length; chunkIdx++) {
      allChunks.push({
        chunk: chunks[chunkIdx],
        chunkIndex: chunkIdx,
        docIndex: batchStartIndex + docIdx,
        document,
        documentId,
      });
    }
  }

  if (allChunks.length === 0) {
    return { chunksCreated: 0, failed, indexed: 0 };
  }

  enforceChunkLimit(allChunks.length, {
    batchStartIndex,
    chunkOverlap: config.chunkOverlap,
    chunkSize: config.chunkSize,
    documentCount: batch.length,
  });

  // Generate embeddings for all chunks in batch
  const { embeddings } = await embedMany({
    abortSignal: AbortSignal.timeout(
      getEmbedTimeoutMs(allChunks.length, config.maxParallelCalls)
    ),
    maxParallelCalls: config.maxParallelCalls,
    model: getTextEmbeddingModel(),
    values: allChunks.map((c) => c.chunk),
  });

  if (embeddings.length !== allChunks.length) {
    throw new Error(
      `Embedding count mismatch: expected ${allChunks.length}, got ${embeddings.length}`
    );
  }

  assertEmbeddingDimensions(embeddings, TEXT_EMBEDDING_DIMENSIONS, "indexBatch");

  // Prepare rows for upsert
  const rows: Database["public"]["Tables"]["rag_documents"]["Insert"][] = allChunks.map(
    (item, idx) => ({
      // biome-ignore lint/style/useNamingConvention: Database field name
      chat_id: chatId ?? null,
      // biome-ignore lint/style/useNamingConvention: Database field name
      chunk_index: item.chunkIndex,
      content: item.chunk,
      embedding: toPgvector(embeddings[idx]),
      // NOTE: `id` is the document identifier; chunk uniqueness is handled via `chunk_index`.
      // Changing `id` to include `chunk_index` breaks upsert deduplication on (id, chunk_index)
      // and violates the RagDocument/RagChunk UUID semantics.
      id: item.documentId,
      metadata: (item.document.metadata ??
        {}) as Database["public"]["Tables"]["rag_documents"]["Insert"]["metadata"],
      namespace: config.namespace,
      // biome-ignore lint/style/useNamingConvention: Database field name
      source_id: item.document.sourceId ?? null,
      // biome-ignore lint/style/useNamingConvention: Database field name
      trip_id: tripId ?? null,
      // biome-ignore lint/style/useNamingConvention: Database field name
      user_id: userId,
    })
  );

  // Upsert to database
  const { error } = await upsertMany(supabase, "rag_documents", rows, "id,chunk_index");

  if (error) {
    throw new Error(
      `Database upsert failed: ${error instanceof Error ? error.message : String(error)}`
    );
  }

  // Count successful documents (unique doc indices)
  const successfulDocIndices = new Set(allChunks.map((c) => c.docIndex));
  indexed = successfulDocIndices.size;
  chunksCreated = rows.length;

  return { chunksCreated, failed, indexed };
}

/**
 * Delete all documents in a namespace.
 *
 * @param supabase - Supabase client instance.
 * @param namespace - Namespace to clear.
 * @returns Count of deleted documents.
 * @throws Error when the namespace delete fails.
 * @see docs/specs/active/0104-spec-rag.md
 */
export async function deleteNamespace(
  supabase: SupabaseClient<Database>,
  namespace: RagNamespace
): Promise<number> {
  const { count, error } = await deleteMany(supabase, "rag_documents", (qb) =>
    qb.eq("namespace", namespace)
  );

  if (error) {
    throw new Error(
      `Failed to delete namespace: ${error instanceof Error ? error.message : String(error)}`
    );
  }

  logger.info("namespace_deleted", {
    count: count ?? 0,
    namespace,
  });

  return count ?? 0;
}
