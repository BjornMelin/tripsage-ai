/**
 * @fileoverview Supabase-centric memory orchestrator.
 *
 * Defines MemoryIntent, adapter interfaces, and the orchestrator pipeline
 * that fans out to Supabase, Upstash, and Mem0 adapters with telemetry and
 * basic PII redaction for non-canonical providers.
 */

import "server-only";

import type { MemoryContextResponse, Message } from "@schemas/chat";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import { createMem0Adapter } from "./mem0-adapter";
import { createSupabaseMemoryAdapter } from "./supabase-adapter";
import { createUpstashMemoryAdapter } from "./upstash-adapter";

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
   * Supabase canonical adapter should populate this from the primary store;
   * Mem0 adapter may append enriched context snippets.
   */
  contextItems?: MemoryContextResponse[];
}

/** Adapter interface for memory backends. */
export interface MemoryAdapter {
  /** Stable adapter identifier (e.g., "supabase", "upstash", "mem0"). */
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

/** Simple PII redaction result. */
type PiiRedactionResult = {
  hadPii: boolean;
  redacted: string;
};

/**
 * Redact basic PII patterns (emails, phone numbers, card-like numbers) from text.
 * Intended for non-canonical adapters (Mem0, Upstash) where content leaves
 * the primary datastore.
 */
function redactPii(text: string): PiiRedactionResult {
  let hadPii = false;

  const replace = () => {
    hadPii = true;
    return "[REDACTED]";
  };

  // Email addresses
  const emailRegex = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g;
  // Phone numbers (basic)
  const phoneRegex = /\+?[0-9][0-9()[\]\-.\s]{6,}[0-9]/g;
  // Card-like digit sequences
  const cardRegex = /\b(?:\d[ -]?){13,16}\b/g;

  let redacted = text.replace(emailRegex, replace);
  redacted = redacted.replace(phoneRegex, replace);
  redacted = redacted.replace(cardRegex, replace);

  return { hadPii, redacted };
}

/**
 * Derive a sanitized version of the intent for non-Supabase adapters.
 * Currently only redacts `turn.content` for `onTurnCommitted` intents.
 */
function buildSanitizedIntent(intent: MemoryIntent): {
  canonical: MemoryIntent;
  sanitizedForSecondary: MemoryIntent;
  piiScrubbed: boolean;
} {
  if (intent.type !== "onTurnCommitted") {
    return {
      canonical: intent,
      piiScrubbed: false,
      sanitizedForSecondary: intent,
    };
  }

  const { turn } = intent;
  const { hadPii, redacted } = redactPii(turn.content);

  if (!hadPii) {
    return {
      canonical: intent,
      piiScrubbed: false,
      sanitizedForSecondary: intent,
    };
  }

  const sanitizedTurn: Message = {
    ...turn,
    content: redacted,
  };

  return {
    canonical: intent,
    piiScrubbed: true,
    sanitizedForSecondary: {
      ...intent,
      turn: sanitizedTurn,
    },
  };
}

/**
 * Run the memory orchestrator for a given intent with explicit configuration.
 *
 * @param intent Memory intent to handle.
 * @param options Orchestrator configuration (adapters and optional clock).
 * @returns Aggregated orchestrator result.
 */
export function runMemoryOrchestrator(
  intent: MemoryIntent,
  options: MemoryOrchestratorOptions
): Promise<MemoryOrchestratorResult> {
  const clock = options.clock ?? Date.now;

  const { canonical, sanitizedForSecondary } = buildSanitizedIntent(intent);

  return withTelemetrySpan<MemoryOrchestratorResult>(
    "memory.orchestrator",
    {
      attributes: {
        "memory.intent.type": canonical.type,
        "memory.session.id": canonical.sessionId,
        "memory.user.id": canonical.userId,
      },
      redactKeys: ["memory.user.id"],
    },
    async () => {
      const ctx: MemoryAdapterContext = { now: clock };
      const results: MemoryAdapterResult[] = [];
      const aggregatedContext: MemoryContextResponse[] = [];

      let hadError = false;
      let anySuccess = false;

      for (const adapter of options.adapters) {
        if (!adapter.supportedIntents.includes(canonical.type)) {
          results.push({
            adapterId: adapter.id,
            intentType: canonical.type,
            status: "skipped",
          });
          continue;
        }

        const start = clock();
        const isCanonicalAdapter = adapter.id === "supabase";
        const adapterIntent = isCanonicalAdapter ? canonical : sanitizedForSecondary;

        try {
          const execResult = await withTelemetrySpan<MemoryAdapterExecutionResult>(
            `memory.adapter.${adapter.id}`,
            {
              attributes: {
                "memory.adapter.id": adapter.id,
                "memory.intent.type": adapterIntent.type,
              },
            },
            async () => adapter.handle(adapterIntent, ctx)
          );

          const durationMs = clock() - start;
          const fullResult: MemoryAdapterResult = {
            adapterId: adapter.id,
            durationMs,
            intentType: adapterIntent.type,
            ...execResult,
          };

          if (execResult.contextItems && execResult.contextItems.length > 0) {
            aggregatedContext.push(...execResult.contextItems);
          }

          if (execResult.status === "error") {
            hadError = true;
          } else if (execResult.status === "ok") {
            anySuccess = true;
          }

          results.push(fullResult);
        } catch (error) {
          const durationMs = clock() - start;
          hadError = true;
          results.push({
            adapterId: adapter.id,
            durationMs,
            error: error instanceof Error ? error.message : "unknown_error",
            intentType: adapterIntent.type,
            status: "error",
          });
        }
      }

      const status: MemoryOrchestratorResult["status"] =
        hadError && anySuccess ? "partial" : hadError ? "error" : "ok";

      const context =
        canonical.type === "fetchContext" && aggregatedContext.length > 0
          ? aggregatedContext
          : undefined;

      return {
        context,
        intent: canonical,
        results,
        status,
      };
    }
  );
}

/**
 * Build the default orchestrator configuration using Supabase, Upstash, and Mem0 adapters.
 *
 * Mem0 adapter is included only when environment/configuration allows it
 * (e.g., MEM0_API_KEY or equivalent is present).
 */
export function createDefaultMemoryOrchestratorOptions(): MemoryOrchestratorOptions {
  const adapters: MemoryAdapter[] = [
    createSupabaseMemoryAdapter(),
    createUpstashMemoryAdapter(),
  ];

  const mem0Adapter = createMem0Adapter();
  if (mem0Adapter) {
    adapters.push(mem0Adapter);
  }

  return {
    adapters,
  };
}

/**
 * Convenience helper for running the orchestrator with default adapters.
 *
 * @param intent Memory intent to handle.
 * @returns Aggregated orchestrator result.
 */
export function handleMemoryIntent(
  intent: MemoryIntent
): Promise<MemoryOrchestratorResult> {
  const options = createDefaultMemoryOrchestratorOptions();
  return runMemoryOrchestrator(intent, options);
}
