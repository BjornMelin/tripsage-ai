/**
 * @fileoverview Supabase-centric memory orchestrator.
 */

import "server-only";

import type { MemoryContextResponse, Message } from "@schemas/chat";
import { hashTelemetryIdentifier } from "@/lib/telemetry/identifiers";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import { createMem0Adapter } from "./mem0-adapter";
import { createSupabaseMemoryAdapter } from "./supabase-adapter";
import type {
  MemoryAdapter,
  MemoryAdapterContext,
  MemoryAdapterExecutionResult,
  MemoryAdapterResult,
  MemoryIntent,
  MemoryOrchestratorOptions,
  MemoryOrchestratorResult,
} from "./types";
import { createUpstashMemoryAdapter } from "./upstash-adapter";

// Re-export types for backwards compatibility
export type {
  MemoryAdapter,
  MemoryAdapterContext,
  MemoryAdapterExecutionResult,
  MemoryAdapterExecutionStatus,
  MemoryAdapterResult,
  MemoryIntent,
  MemoryIntentType,
  MemoryOrchestratorOptions,
  MemoryOrchestratorResult,
} from "./types";

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
  const sessionIdHash = hashTelemetryIdentifier(canonical.sessionId);
  const userIdHash = hashTelemetryIdentifier(canonical.userId);

  return withTelemetrySpan<MemoryOrchestratorResult>(
    "memory.orchestrator",
    {
      attributes: {
        "memory.intent.type": canonical.type,
        ...(sessionIdHash ? { "session.id_hash": sessionIdHash } : {}),
        ...(userIdHash ? { "user.id_hash": userIdHash } : {}),
      },
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
