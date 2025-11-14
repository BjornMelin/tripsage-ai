/**
 * @fileoverview Zod schemas for webhook payloads and jobs.
 */

import { z } from "zod";

/** Zod schema for webhook payload validation. */
export const webhookPayloadSchema = z.object({
  occurredAt: z.string().optional(),
  oldRecord: z.record(z.string(), z.any()).nullable().default(null),
  record: z.record(z.string(), z.any()).nullable(),
  schema: z.string().optional(),
  table: z.string().min(1),
  type: z.enum(["INSERT", "UPDATE", "DELETE"]),
});

/** TypeScript type inferred from webhookPayloadSchema. */
export type WebhookPayload = z.infer<typeof webhookPayloadSchema>;

/** Zod schema for collaborator notification job validation. */
export const notifyJobSchema = z.object({
  eventKey: z.string().min(8),
  payload: webhookPayloadSchema,
});

/** TypeScript type inferred from notifyJobSchema. */
export type NotifyJob = z.infer<typeof notifyJobSchema>;
