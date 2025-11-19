/**
 * @fileoverview Webhook payload and job schemas with validation.
 * Includes webhook payloads, notification jobs, and memory sync jobs.
 */

import { z } from "zod";
import { primitiveSchemas } from "./registry";

// ===== CORE SCHEMAS =====
// Core business logic schemas for webhook handling

/**
 * Zod schema for webhook payload validation.
 * Validates Supabase webhook payload structure including record changes and event type.
 */
export const webhookPayloadSchema = z.object({
  occurredAt: primitiveSchemas.isoDateTime.optional(),
  oldRecord: z.record(z.string(), z.any()).nullable().default(null),
  record: z.record(z.string(), z.any()).nullable(),
  schema: z.string().optional(),
  table: z.string().min(1),
  type: z.enum(["INSERT", "UPDATE", "DELETE"]),
});

/** TypeScript type for webhook payloads. */
export type WebhookPayload = z.infer<typeof webhookPayloadSchema>;

/**
 * Zod schema for collaborator notification job validation.
 * Validates notification job structure including event key and payload.
 */
export const notifyJobSchema = z.object({
  eventKey: z.string().min(8),
  payload: webhookPayloadSchema,
});

/** TypeScript type for notification jobs. */
export type NotifyJob = z.infer<typeof notifyJobSchema>;

/**
 * Zod schema for memory sync job validation.
 * Validates memory synchronization job structure including conversation messages and sync type.
 */
export const memorySyncJobSchema = z.object({
  idempotencyKey: z.string().min(8),
  payload: z.object({
    conversationMessages: z
      .array(
        z.object({
          content: z.string(),
          metadata: z.record(z.string(), z.unknown()).optional(),
          role: z.enum(["user", "assistant", "system"]),
          timestamp: primitiveSchemas.isoDateTime,
        })
      )
      .optional(),
    sessionId: primitiveSchemas.uuid,
    syncType: z.enum(["full", "incremental", "conversation"]),
    userId: primitiveSchemas.uuid,
  }),
});

/** TypeScript type for memory sync jobs. */
export type MemorySyncJob = z.infer<typeof memorySyncJobSchema>;
