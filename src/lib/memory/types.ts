/**
 * @fileoverview Shared types for the memory orchestrator and adapters to avoid circular dependencies.
 */

import type { MemoryContextResponse, Message } from "@schemas/chat";

/** Supported memory intent types. */
export type MemoryIntentType =
  | "onTurnCommitted"
  | "syncSession"
  | "backfillSession"
  | "fetchContext";

/** Memory orchestrator intent payloads. */
export type MemoryIntent =
  | {
      type: "onTurnCommitted";
      sessionId: string;
      userId: string;
      turn: Message;
    }
  | {
      type: "syncSession";
      sessionId: string;
      userId: string;
    }
  | {
      type: "backfillSession";
      sessionId: string;
      userId: string;
    }
  | {
      type: "fetchContext";
      sessionId: string;
      userId: string;
      limit?: number;
      /**
       * Optional query for semantic search. When provided, the adapter uses
       * vector similarity search against turn embeddings. When omitted, falls
       * back to recency-based retrieval.
       */
      query?: string;
      /**
       * Optional similarity threshold for semantic search results (0..1).
       * When omitted, adapters should use a reasonable default.
       */
      similarityThreshold?: number;
    };

/** Execution context passed to adapters. */
export interface MemoryAdapterContext {
  /** Monotonic clock in milliseconds. */
  now: () => number;
}

/** Per-adapter execution status. */
export type MemoryAdapterExecutionStatus = "ok" | "skipped" | "error";

/** Minimal result shape returned by adapters. */
export interface MemoryAdapterExecutionResult {
  status: MemoryAdapterExecutionStatus;
  error?: string;
  /**
   * Optional context items produced by adapters for fetchContext intents.
   * Supabase canonical adapter should populate this from the primary store
   * (optionally using semantic search), and other adapters (e.g. Upstash) may
   * append additional context snippets.
   */
  contextItems?: MemoryContextResponse[];
}

/** Adapter interface for memory backends. */
export interface MemoryAdapter {
  /** Stable adapter identifier (e.g., "supabase", "upstash"). */
  id: string;
  /** Intents this adapter can handle. */
  supportedIntents: MemoryIntentType[];
  /**
   * Handle a memory intent.
   *
   * Implementations should treat errors as localized and return status "error"
   * rather than throwing, except for truly unexpected failures.
   */
  handle(
    intent: MemoryIntent,
    ctx: MemoryAdapterContext
  ): Promise<MemoryAdapterExecutionResult>;
}

/** Result for a single adapter after orchestration. */
export interface MemoryAdapterResult extends MemoryAdapterExecutionResult {
  adapterId: string;
  intentType: MemoryIntentType;
  durationMs?: number;
}

/** Aggregate orchestrator result across all adapters. */
export interface MemoryOrchestratorResult {
  intent: MemoryIntent;
  status: "ok" | "partial" | "error";
  results: MemoryAdapterResult[];
  /**
   * Aggregated context items merged from all adapters for fetchContext intents.
   * For non-fetch intents this will be undefined.
   */
  context?: MemoryContextResponse[];
}

/** Orchestrator configuration. */
export interface MemoryOrchestratorOptions {
  adapters: MemoryAdapter[];
  /** Optional clock implementation for testing. Defaults to Date.now. */
  clock?: () => number;
}
