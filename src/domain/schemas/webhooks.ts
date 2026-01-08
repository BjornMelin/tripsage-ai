/**
 * @fileoverview Webhook payload and job schemas with validation. Includes webhook payloads, notification jobs, and memory sync jobs.
 */

import { z } from "zod";
import {
  MAX_RAG_INDEX_TOTAL_CONTENT_CHARS,
  ragDocumentSchema,
  ragNamespaceSchema,
} from "./rag";
import { primitiveSchemas } from "./registry";

// ===== CORE SCHEMAS =====
// Core business logic schemas for webhook handling

/**
 * Zod schema for webhook payload validation.
 * Validates Supabase webhook payload structure including record changes and event type.
 */
export const webhookPayloadSchema = z.object({
  occurredAt: primitiveSchemas.isoDateTime.optional(),
  oldRecord: z.looseRecord(z.string(), z.unknown()).nullable().default(null),
  record: z.looseRecord(z.string(), z.unknown()).nullable(),
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
          metadata: z.looseRecord(z.string(), z.unknown()).optional(),
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

// ===== JOB SCHEMAS =====

/**
 * QStash job for ingesting a single uploaded attachment (download + text extraction).
 */
export const attachmentsIngestJobSchema = z.strictObject({
  attachmentId: primitiveSchemas.uuid,
});

export type AttachmentsIngestJob = z.infer<typeof attachmentsIngestJobSchema>;

/**
 * QStash job for indexing documents into the RAG store.
 *
 * This is a server-side equivalent of the `/api/rag/index` request shape, with explicit
 * scoping fields for user and optional trip/chat context.
 */
export const ragIndexJobSchema = z
  .strictObject({
    chatId: primitiveSchemas.uuid.nullable().optional(),
    chunkOverlap: z.number().int().min(0).max(500).default(100),
    chunkSize: z.number().int().min(100).max(2000).default(512),
    documents: z.array(ragDocumentSchema).min(1).max(100, {
      error: "Maximum 100 documents per batch",
    }),
    namespace: ragNamespaceSchema.default("user_content"),
    tripId: z.number().int().nonnegative().nullable().optional(),
    userId: primitiveSchemas.uuid,
  })
  .refine(
    (value) =>
      value.documents.reduce((total, doc) => total + doc.content.length, 0) <=
      MAX_RAG_INDEX_TOTAL_CONTENT_CHARS,
    {
      error: `Total document content exceeds ${MAX_RAG_INDEX_TOTAL_CONTENT_CHARS} characters`,
      path: ["documents"],
    }
  );

export type RagIndexJob = z.infer<typeof ragIndexJobSchema>;
