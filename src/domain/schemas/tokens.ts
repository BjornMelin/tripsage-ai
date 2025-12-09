/**
 * @fileoverview Token counting, budgeting, and model limits schemas.
 * Includes chat message roles, token counting messages, clamp results, and model limits.
 */

import { z } from "zod";

// ===== CORE SCHEMAS =====
// Core business logic schemas for token management

/**
 * Zod schema for chat message roles.
 * Defines available roles for chat messages in token counting.
 */
export const chatMessageRoleSchema = z.enum(["system", "user", "assistant"]);

/** TypeScript type for chat message roles. */
export type ChatMessageRole = z.infer<typeof chatMessageRoleSchema>;

/**
 * Zod schema for chat messages used in token counting.
 * Validates message structure including content and role.
 */
export const tokenChatMessageSchema = z.object({
  content: z.string(),
  role: chatMessageRoleSchema,
});

/** TypeScript type for chat messages used in token counting. */
export type TokenChatMessage = z.infer<typeof tokenChatMessageSchema>;

/**
 * Zod schema for token clamp result.
 * Validates token clamping result including final max tokens and reasons.
 */
export const clampResultSchema = z.object({
  /** Final safe max tokens for the model/context. */
  maxTokens: z.number().int().min(1),
  /** Reasons describing why clamping occurred. */
  reasons: z.array(z.string()),
});

/** TypeScript type for clamp result. */
export type ClampResult = z.infer<typeof clampResultSchema>;

/**
 * Zod schema for model limits table (key-value mapping of model names to context limits).
 * Validates model name to context limit mappings.
 */
export const modelLimitsTableSchema = z.record(z.string(), z.number().int().positive());

/** TypeScript type for model limits table. */
export type ModelLimitsTable = z.infer<typeof modelLimitsTableSchema>;
