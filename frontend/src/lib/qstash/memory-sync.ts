/**
 * @fileoverview QStash memory sync job enqueue utilities.
 * Provides typed helpers for enqueuing memory sync operations with proper
 * deduplication and error handling.
 */

import "server-only";

import type { MemorySyncJob } from "@schemas/webhooks";
import { Client } from "@upstash/qstash";
import { getClientEnvVarWithFallback } from "@/lib/env/client";
import { getServerEnvVar } from "@/lib/env/server";
import { secureUuid } from "@/lib/security/random";

/**
 * Get configured QStash client for memory sync operations.
 *
 * @return QStash client instance.
 */
function getQstashClient(): Client {
  const token = getServerEnvVar("QSTASH_TOKEN") as string;
  return new Client({ token });
}

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
  const client = getQstashClient();
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

  // Use client env helper for NEXT_PUBLIC_ variables (safe in server context)
  // Fallback to APP_BASE_URL from server env if available
  let baseUrl = getClientEnvVarWithFallback("NEXT_PUBLIC_SITE_URL", "");
  if (!baseUrl) {
    try {
      baseUrl = getServerEnvVar("APP_BASE_URL") as string;
    } catch {
      baseUrl = "http://localhost:3000";
    }
  }
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
