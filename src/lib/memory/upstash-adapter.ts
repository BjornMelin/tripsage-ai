/**
 * @fileoverview Upstash adapter for memory orchestrator.
 *
 * Delegates durable memory sync operations to QStash-backed jobs and uses
 * Upstash Redis for best-effort ephemeral state when available.
 */

import "server-only";

import {
  enqueueConversationMemorySync,
  enqueueFullMemorySync,
  enqueueIncrementalMemorySync,
} from "@/lib/qstash/memory-sync";
import { getRedis } from "@/lib/redis";
import type {
  MemoryAdapter,
  MemoryAdapterContext,
  MemoryAdapterExecutionResult,
  MemoryIntent,
} from "./orchestrator";

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
    await enqueueConversationMemorySync(intent.sessionId, intent.userId, messages);
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
    if (intent.type === "syncSession") {
      await enqueueIncrementalMemorySync(intent.sessionId, intent.userId);
    } else {
      await enqueueFullMemorySync(intent.sessionId, intent.userId);
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
