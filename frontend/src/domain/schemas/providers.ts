/**
 * @fileoverview AI provider registry and model resolution schemas.
 * Includes provider identifiers, resolution results, and model mapper types.
 */

import { z } from "zod";

// ===== CORE SCHEMAS =====
// Core business logic schemas for AI provider management

/**
 * Zod schema for provider identifiers.
 * Defines supported AI providers in the system.
 */
export const providerIdSchema = z.enum(["openai", "openrouter", "anthropic", "xai"]);

/** TypeScript type for provider identifiers. */
export type ProviderId = z.infer<typeof providerIdSchema>;

/**
 * Zod schema for provider resolution result.
 * Validates resolved provider configuration including model ID and token limits.
 */
export const providerResolutionSchema = z.object({
  /** Optional conservative token budget for downstream routing. */
  maxTokens: z.number().int().positive().optional(),
  /** Resolved model identifier (provider-specific). */
  modelId: z.string().min(1),
  /** Selected provider id. */
  provider: providerIdSchema,
  /** AI SDK LanguageModel (not serializable, excluded from schema). */
  // Note: model field is LanguageModel from 'ai' package, not serializable
});

/** TypeScript type for provider resolution (model field added at runtime). */
export type ProviderResolution = z.infer<typeof providerResolutionSchema> & {
  /** AI SDK LanguageModel, ready to pass to streamText/generateText. */
  model: unknown; // LanguageModel from 'ai' package
};

/**
 * Zod schema for model mapper function signature (not directly serializable).
 * Note: This is a type-only schema for documentation purposes.
 */
export type ModelMapper = (provider: ProviderId, modelHint?: string) => string;
