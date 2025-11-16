/**
 * @fileoverview Zod v4 schemas for token counting, budgeting, and model limits.
 */

import { z } from "zod";

/** Zod schema for chat message roles. */
export const chatMessageRoleSchema = z.enum(["system", "user", "assistant"]);
/** TypeScript type for chat message roles. */
export type ChatMessageRole = z.infer<typeof chatMessageRoleSchema>;

/** Zod schema for chat messages used in token counting. */
export const tokenChatMessageSchema = z.object({
  content: z.string(),
  role: chatMessageRoleSchema,
});
/** TypeScript type for chat messages used in token counting. */
export type TokenChatMessage = z.infer<typeof tokenChatMessageSchema>;

/** Zod schema for token clamp result. */
export const clampResultSchema = z.object({
  /** Final safe max tokens for the model/context. */
  maxTokens: z.number().int().min(1),
  /** Reasons describing why clamping occurred. */
  reasons: z.array(z.string()),
});
/** TypeScript type for clamp result. */
export type ClampResult = z.infer<typeof clampResultSchema>;

/** Zod schema for model limits table (key-value mapping of model names to context limits). */
export const modelLimitsTableSchema = z.record(z.string(), z.number().int().positive());
/** TypeScript type for model limits table. */
export type ModelLimitsTable = z.infer<typeof modelLimitsTableSchema>;
