/**
 * @fileoverview Schemas for embeddings-related API boundaries.
 */

import { z } from "zod";

// ===== API REQUEST SCHEMAS =====

export const embeddingsPropertySchema = z.strictObject({
  amenities: z.union([z.array(z.string()), z.string()]).optional(),
  description: z.string().optional(),
  id: z.string().min(1).optional(),
  name: z.string().optional(),
  source: z.string().optional(),
});

export type EmbeddingsProperty = z.infer<typeof embeddingsPropertySchema>;

export const embeddingsRequestSchema = z
  .strictObject({
    property: embeddingsPropertySchema.optional(),
    text: z.string().optional(),
  })
  .refine((data) => data.property !== undefined || data.text !== undefined, {
    error: "Property or text is required",
    path: ["property"],
  });

export type EmbeddingsRequest = z.infer<typeof embeddingsRequestSchema>;

export const persistableEmbeddingsPropertySchema = embeddingsPropertySchema.extend({
  id: z.string().min(1, { error: "Property id is required" }),
});

export type PersistableEmbeddingsProperty = z.infer<
  typeof persistableEmbeddingsPropertySchema
>;
