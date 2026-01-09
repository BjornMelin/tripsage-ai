/**
 * @fileoverview Error types for RAG indexing operations.
 */

/**
 * Options for RagLimitError, providing context about chunk-limit violations.
 */
export interface RagLimitErrorOptions {
  /** Number of chunks that exceeded the limit. */
  chunkCount?: number;
  /** Maximum allowed chunks. */
  limit?: number;
}

/**
 * Error thrown when RAG indexing exceeds configured chunk limits.
 */
export class RagLimitError extends Error {
  readonly code = "rag_limit:too_many_chunks";
  readonly chunkCount?: number;
  readonly limit?: number;

  constructor(message: string = "too_many_chunks", options?: RagLimitErrorOptions) {
    super(message);
    this.name = "RagLimitError";
    Object.setPrototypeOf(this, RagLimitError.prototype);
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, RagLimitError);
    }
    this.chunkCount = options?.chunkCount;
    this.limit = options?.limit;
  }
}
