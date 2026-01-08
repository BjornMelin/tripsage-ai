/**
 * @fileoverview Upstash adapter for memory orchestrator.
 */

import "server-only";

import { tryEnqueueJob } from "@/lib/qstash/client";
import { getRedis } from "@/lib/redis";
import type {
  MemoryAdapter,
  MemoryAdapterContext,
  MemoryAdapterExecutionResult,
  MemoryIntent,
} from "./types";

async function handleOnTurnCommitted(
  intent: Extract<MemoryIntent, { type: "onTurnCommitted" }>
): Promise<MemoryAdapterExecutionResult> {
  const messages = [
    {
      content: intent.turn.content,
      metadata: {
        attachments: intent.turn.attachments,
        toolCalls: intent.turn.toolCalls,
        toolResults: intent.turn.toolResults,
      },
      role: intent.turn.role,
      timestamp: intent.turn.timestamp,
    },
  ];

  try {
    const idempotencyKey = `conv-sync:${intent.sessionId}:${intent.turn.id}`;
    const result = await tryEnqueueJob(
      "memory-sync",
      {
        idempotencyKey,
        payload: {
          conversationMessages: messages,
          sessionId: intent.sessionId,
          syncType: "conversation",
          userId: intent.userId,
        },
      },
      "/api/jobs/memory-sync",
      {
        deduplicationId: `memory-sync:${idempotencyKey}`,
        delay: 1,
      }
    );
    if (!result.success) {
      throw result.error ?? new Error("qstash_unavailable");
    }
    return { status: "ok" };
  } catch (error) {
    return {
      error:
        error instanceof Error
          ? `qstash_conversation_enqueue_failed:${error.message}`
          : "qstash_conversation_enqueue_failed",
      status: "error",
    };
  }
}

async function handleSyncSession(
  intent: Extract<MemoryIntent, { type: "syncSession" | "backfillSession" }>
): Promise<MemoryAdapterExecutionResult> {
  try {
    const isFull = intent.type === "backfillSession";
    const idempotencyKey = `${isFull ? "full" : "incr"}-sync:${intent.sessionId}`;

    const result = await tryEnqueueJob(
      "memory-sync",
      {
        idempotencyKey,
        payload: {
          sessionId: intent.sessionId,
          syncType: isFull ? "full" : "incremental",
          userId: intent.userId,
        },
      },
      "/api/jobs/memory-sync",
      {
        deduplicationId: `memory-sync:${idempotencyKey}`,
        delay: isFull ? undefined : 5,
      }
    );

    if (!result.success) {
      throw result.error ?? new Error("qstash_unavailable");
    }
    return { status: "ok" };
  } catch (error) {
    return {
      error:
        error instanceof Error
          ? `qstash_sync_enqueue_failed:${error.message}`
          : "qstash_sync_enqueue_failed",
      status: "error",
    };
  }
}

async function writeEphemeralSessionHint(
  intent: MemoryIntent,
  ctx: MemoryAdapterContext
): Promise<void> {
  const redis = getRedis();
  if (!redis) return;

  const key = `memory:session:last-intent:${intent.sessionId}`;
  const payload = {
    intentType: intent.type,
    sessionId: intent.sessionId,
    // TTL-friendly timestamp
    ts: ctx.now(),
    userId: intent.userId,
  };

  try {
    await redis.set(key, JSON.stringify(payload), { ex: 60 * 10 });
  } catch {
    // Best-effort cache; ignore errors
  }
}

/**
 * Create Upstash memory adapter.
 *
 * Responsibilities:
 * - Queue durable memory sync jobs via QStash for conversation, full, and incremental syncs.
 * - Maintain optional ephemeral hints in Redis to aid observability/debugging.
 */
export function createUpstashMemoryAdapter(): MemoryAdapter {
  return {
    async handle(
      intent: MemoryIntent,
      ctx: MemoryAdapterContext
    ): Promise<MemoryAdapterExecutionResult> {
      let result: MemoryAdapterExecutionResult = { status: "skipped" };

      if (intent.type === "onTurnCommitted") {
        result = await handleOnTurnCommitted(intent);
      } else if (intent.type === "syncSession" || intent.type === "backfillSession") {
        result = await handleSyncSession(intent);
      }

      // Fire-and-forget: cache last intent for this session
      writeEphemeralSessionHint(intent, ctx).catch(() => undefined);

      return result;
    },
    id: "upstash",
    supportedIntents: ["onTurnCommitted", "syncSession", "backfillSession"],
  };
}
