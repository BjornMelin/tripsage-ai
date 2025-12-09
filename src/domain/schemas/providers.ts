/**
 * @fileoverview AI provider registry and model resolution schemas.
 * Includes provider identifiers, resolution results, and model mapper types.
 */

import type { LanguageModel } from "ai";
import { z } from "zod";

// ===== CORE SCHEMAS =====

/**
 * Zod schema for provider identifiers.
 * Defines supported AI providers in the system.
 */
export const providerIdSchema = z.enum(["openai", "openrouter", "anthropic", "xai"]);

/** TypeScript type for provider identifiers. */
export type ProviderId = z.infer<typeof providerIdSchema>;

/**
 * Zod schema for provider resolution result (serializable fields only).
 * The `model` field is excluded as LanguageModel is not serializable.
 */
export const providerResolutionSchema = z.object({
  maxTokens: z.number().int().positive().optional(),
  modelId: z.string().min(1),
  provider: providerIdSchema,
});

/**
 * TypeScript type for provider resolution result.
 * Extends schema with runtime-only `model` field.
 */
export type ProviderResolution = z.infer<typeof providerResolutionSchema> & {
  model: LanguageModel;
};

/** Map a generic model hint to a provider-specific model id. */
export type ModelMapper = (provider: ProviderId, modelHint?: string) => string;
