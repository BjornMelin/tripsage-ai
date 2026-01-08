/**
 * @fileoverview Error types for RAG indexing operations.
 */

export interface RagLimitErrorOptions {
  chunkCount?: number;
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
    this.chunkCount = options?.chunkCount;
    this.limit = options?.limit;
  }
}
