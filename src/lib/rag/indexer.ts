/**
 * @fileoverview Server-only RAG indexing (chunking + embeddings + storage).
 */

import "server-only";

import { openai } from "@ai-sdk/openai";
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
import { secureUuid } from "@/lib/security/random";
import type { Database } from "@/lib/supabase/database.types";
import { createServerLogger } from "@/lib/telemetry/logger";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import { toPgvector } from "./pgvector";

const logger = createServerLogger("rag.indexer");

/** Token to character ratio approximation (conservative). */
const CHARS_PER_TOKEN = 4;
const MAX_CHUNKS_PER_EMBED_BATCH = 1200;

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
 *   documents: [{ content: "Travel guide...", metadata: { type: "guide" } }],
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
 * Internal batch indexing parameters.
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
 * Internal batch indexing result.
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

  if (allChunks.length > MAX_CHUNKS_PER_EMBED_BATCH) {
    logger.warn("chunk_limit_exceeded", {
      batchStartIndex,
      chunkCount: allChunks.length,
      chunkOverlap: config.chunkOverlap,
      chunkSize: config.chunkSize,
      documentCount: batch.length,
      limit: MAX_CHUNKS_PER_EMBED_BATCH,
    });
    throw new Error("rag_limit:too_many_chunks");
  }

  // Generate embeddings for all chunks in batch
  const { embeddings } = await embedMany({
    model: openai.embeddingModel("text-embedding-3-small"),
    values: allChunks.map((c) => c.chunk),
  });

  if (embeddings.length !== allChunks.length) {
    throw new Error(
      `Embedding count mismatch: expected ${allChunks.length}, got ${embeddings.length}`
    );
  }

  // Prepare rows for upsert
  const rows: Database["public"]["Tables"]["rag_documents"]["Insert"][] = allChunks.map(
    (item, idx) => ({
      // biome-ignore lint/style/useNamingConvention: Database field name
      chat_id: chatId ?? null,
      // biome-ignore lint/style/useNamingConvention: Database field name
      chunk_index: item.chunkIndex,
      content: item.chunk,
      embedding: toPgvector(embeddings[idx]),
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
  const { error } = await supabase.from("rag_documents").upsert(rows, {
    ignoreDuplicates: false,
    onConflict: "id,chunk_index",
  });

  if (error) {
    throw new Error(`Database upsert failed: ${error.message}`);
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
 */
export async function deleteNamespace(
  supabase: SupabaseClient<Database>,
  namespace: RagNamespace
): Promise<number> {
  const { count, error } = await supabase
    .from("rag_documents")
    .delete({ count: "exact" })
    .eq("namespace", namespace);

  if (error) {
    throw new Error(`Failed to delete namespace: ${error.message}`);
  }

  logger.info("namespace_deleted", {
    count: count ?? 0,
    namespace,
  });

  return count ?? 0;
}
