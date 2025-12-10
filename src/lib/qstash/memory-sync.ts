/**
 * @fileoverview QStash memory sync job enqueue utilities.
 * Provides typed helpers for enqueuing memory sync operations with proper
 * deduplication and error handling.
 */

import "server-only";

import type { MemorySyncJob } from "@schemas/webhooks";
import { secureUuid } from "@/lib/security/random";
import { getRequiredServerOrigin } from "@/lib/url/server-origin";
import { getQStashClient } from "./client";

/**
 * Enqueue a memory sync job via QStash with deduplication.
 *
 * @param payload - Memory sync job payload.
 * @param options - Optional enqueue configuration.
 * @return Promise resolving to enqueue result.
 */
export async function enqueueMemorySync(
  payload: MemorySyncJob["payload"],
  options: {
    delay?: number;
    retries?: number;
    idempotencyKey?: string;
  } = {}
): Promise<{ messageId: string; idempotencyKey: string }> {
  const client = getQStashClient();
  const idempotencyKey = options.idempotencyKey ?? secureUuid();

  const job: MemorySyncJob = {
    idempotencyKey,
    payload,
  };

  const enqueueOptions = {
    delay: options.delay,
    headers: {
      "Upstash-Forward-Upstash-Idempotency-Key": idempotencyKey,
    },
    retries: options.retries ?? 3,
  };

  // Use getRequiredServerOrigin which throws in production if not configured
  const baseUrl = getRequiredServerOrigin();
  const result = await client.publishJSON({
    body: job,
    url: `${baseUrl}/api/jobs/memory-sync`,
    ...enqueueOptions,
  });

  return {
    idempotencyKey,
    messageId: result.messageId,
  };
}

/**
 * Enqueue conversation memory storage for a chat session.
 *
 * @param sessionId - Chat session identifier.
 * @param userId - User identifier.
 * @param messages - Conversation messages to store.
 * @return Promise resolving to enqueue result.
 */
export function enqueueConversationMemorySync(
  sessionId: string,
  userId: string,
  messages: Array<{
    content: string;
    role: "user" | "assistant" | "system";
    timestamp: string;
    metadata?: Record<string, unknown>;
  }>
): Promise<{ messageId: string; idempotencyKey: string }> {
  return enqueueMemorySync(
    {
      conversationMessages: messages,
      sessionId,
      syncType: "conversation",
      userId,
    },
    {
      delay: 1000, // Small delay to batch rapid messages
      idempotencyKey: `conv-sync:${sessionId}:${Date.now()}`,
    }
  );
}

/**
 * Enqueue full memory context sync for a session.
 *
 * @param sessionId - Chat session identifier.
 * @param userId - User identifier.
 * @return Promise resolving to enqueue result.
 */
export function enqueueFullMemorySync(
  sessionId: string,
  userId: string
): Promise<{ messageId: string; idempotencyKey: string }> {
  return enqueueMemorySync(
    {
      sessionId,
      syncType: "full",
      userId,
    },
    {
      idempotencyKey: `full-sync:${sessionId}:${Date.now()}`,
    }
  );
}

/**
 * Enqueue incremental memory context update.
 *
 * @param sessionId - Chat session identifier.
 * @param userId - User identifier.
 * @return Promise resolving to enqueue result.
 */
export function enqueueIncrementalMemorySync(
  sessionId: string,
  userId: string
): Promise<{ messageId: string; idempotencyKey: string }> {
  return enqueueMemorySync(
    {
      sessionId,
      syncType: "incremental",
      userId,
    },
    {
      delay: 5000, // Debounce incremental updates
      idempotencyKey: `incr-sync:${sessionId}:${Date.now()}`,
    }
  );
}
