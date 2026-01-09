/**
 * @fileoverview Domain-level errors for memory sync jobs.
 */

export type MemorySyncDatabaseOperation =
  | "session_check"
  | "session_create"
  | "turn_dedupe_lookup"
  | "turn_insert"
  | "session_sync_update"
  | "chat_session_update";

export class MemorySyncAccessError extends Error {
  readonly code = "MEMORY_SYNC_ACCESS" as const;
  readonly sessionId: string;
  readonly userId: string;

  constructor(
    message: string,
    params: {
      sessionId: string;
      userId: string;
    }
  ) {
    super(message);
    this.name = "MemorySyncAccessError";
    this.sessionId = params.sessionId;
    this.userId = params.userId;
    Object.setPrototypeOf(this, MemorySyncAccessError.prototype);
  }
}

export class MemorySyncDatabaseError extends Error {
  readonly code = "MEMORY_SYNC_DB_ERROR" as const;
  readonly operation: MemorySyncDatabaseOperation;
  readonly sessionId: string;
  readonly cause?: unknown;
  readonly context?: Record<string, unknown>;

  constructor(
    message: string,
    params: {
      operation: MemorySyncDatabaseOperation;
      sessionId: string;
      cause?: unknown;
      context?: Record<string, unknown>;
    }
  ) {
    super(message);
    this.name = "MemorySyncDatabaseError";
    this.operation = params.operation;
    this.sessionId = params.sessionId;
    this.cause = params.cause;
    this.context = params.context;
    Object.setPrototypeOf(this, MemorySyncDatabaseError.prototype);
  }
}
