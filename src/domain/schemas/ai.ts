/**
 * @fileoverview AI SDK UI stream metadata and data-part schemas.
 */

import { z } from "zod";
import { agentTypeSchema } from "./configuration";

// ===== CORE SCHEMAS =====

export const languageModelUsageSchema = z.looseObject({
  cachedInputTokens: z.number().int().nonnegative().optional(),
  inputTokenDetails: z
    .looseObject({
      cacheReadTokens: z.number().int().nonnegative().optional(),
      cacheWriteTokens: z.number().int().nonnegative().optional(),
      noCacheTokens: z.number().int().nonnegative().optional(),
    })
    .optional(),
  inputTokens: z.number().int().nonnegative().optional(),
  outputTokenDetails: z
    .looseObject({
      reasoningTokens: z.number().int().nonnegative().optional(),
      textTokens: z.number().int().nonnegative().optional(),
    })
    .optional(),
  outputTokens: z.number().int().nonnegative().optional(),
  raw: z.unknown().optional(),
  reasoningTokens: z.number().int().nonnegative().optional(),
  totalTokens: z.number().int().nonnegative().optional(),
});

export type LanguageModelUsageMetadata = z.infer<typeof languageModelUsageSchema>;

export const chatMessageMetadataSchema = z.looseObject({
  finishReason: z.string().nullable().optional(),
  requestId: z.string().optional(),
  sessionId: z.string().optional(),
  totalUsage: languageModelUsageSchema.nullable().optional(),
});

export type ChatMessageMetadata = z.infer<typeof chatMessageMetadataSchema>;

export const agentMessageMetadataSchema = z.looseObject({
  agentType: agentTypeSchema,
  finishReason: z.string().nullable().optional(),
  modelId: z.string().min(1),
  requestId: z.string().optional(),
  totalUsage: languageModelUsageSchema.nullable().optional(),
  versionId: z.string().optional(),
});

export type AgentMessageMetadata = z.infer<typeof agentMessageMetadataSchema>;

export const aiStreamStatusSchema = z.strictObject({
  kind: z.enum(["start", "finish", "tool"]),
  label: z.string().min(1).max(200),
  step: z.number().int().positive().optional(),
});

export type AiStreamStatus = z.infer<typeof aiStreamStatusSchema>;

export const chatDataPartSchemas = {
  status: aiStreamStatusSchema,
} satisfies Record<string, z.ZodTypeAny>;

// ===== FORM SCHEMAS =====

// ===== TOOL INPUT SCHEMAS =====
