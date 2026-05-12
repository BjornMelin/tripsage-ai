/**
 * @fileoverview Model context window limits (in tokens) and helpers. Maintains per-model context limits for safe clamping in AI SDK calls.
 */

import type { ModelLimitsTable } from "@schemas/tokens";

// Re-export type from schemas
export type { ModelLimitsTable };

/** Canonical app-owned OpenAI model profiles. */
export const MODEL_PROFILES = {
  planning: {
    directModelId: "gpt-5.5",
    gatewayModelId: "openai/gpt-5.5",
    maxContextTokens: 1_050_000,
    maxOutputTokens: 128_000,
  },
  standard: {
    directModelId: "gpt-5.4-mini",
    gatewayModelId: "openai/gpt-5.4-mini",
    maxContextTokens: 400_000,
    maxOutputTokens: 128_000,
  },
  utility: {
    directModelId: "gpt-5.4-nano",
    gatewayModelId: "openai/gpt-5.4-nano",
    maxContextTokens: 400_000,
    maxOutputTokens: 128_000,
  },
} as const;

/** Supported model profile identifiers. */
export type ModelProfileId = keyof typeof MODEL_PROFILES;

const PROFILE_MODEL_LIMITS = Object.fromEntries(
  Object.values(MODEL_PROFILES).map(({ directModelId, maxContextTokens }) => [
    directModelId,
    maxContextTokens,
  ])
) satisfies ModelLimitsTable;

/**
 * Canonical context window limits (tokens) for known models.
 * Keys are normalized lowercase substrings matched against model names.
 */
export const MODEL_LIMITS: ModelLimitsTable = {
  // DeepSeek
  "deepseek-v4-flash": 1_000_000,
  "deepseek-v4-pro": 1_000_000,
  // Google
  "gemini-3.1-flash-lite": 1_000_000,
  // Z.ai
  "glm-5.1": 131_072,

  // xAI
  "grok-4.3": 1_000_000,
  // Moonshot AI
  "kimi-k2.6": 262_000,
  "mimo-v2.5": 1_000_000,
  // Xiaomi
  "mimo-v2.5-pro": 1_000_000,
  // OpenAI app-owned profiles
  ...PROFILE_MODEL_LIMITS,
};

/** Default context window (tokens) when model is unknown. */
export const DEFAULT_CONTEXT_LIMIT = 128_000;

const sortedDefaultLimitKeys = Object.keys(MODEL_LIMITS).sort(
  (a, b) => b.length - a.length
);

function getSortedLimitKeys(table: ModelLimitsTable): string[] {
  if (table === MODEL_LIMITS) return sortedDefaultLimitKeys;
  return Object.keys(table).sort((a, b) => b.length - a.length);
}

/**
 * Resolve the context window limit for a given model.
 * Performs a lowercase substring match against known keys.
 *
 * @param modelName - The model identifier (e.g., "gpt-5.5").
 * @param table - Optional override table.
 * @returns - Context window token limit.
 */
export function getModelContextLimit(
  modelName: string | undefined,
  table: ModelLimitsTable = MODEL_LIMITS
): number {
  if (!modelName) return DEFAULT_CONTEXT_LIMIT;
  const name = modelName.toLowerCase();
  for (const key of getSortedLimitKeys(table)) {
    if (name.includes(key)) return table[key];
  }
  return DEFAULT_CONTEXT_LIMIT;
}
