/**
 * @fileoverview Model context window limits (in tokens) and helpers. Maintains per-model context limits for safe clamping in AI SDK calls.
 */

import type { ModelLimitsTable } from "@schemas/tokens";

// Re-export type from schemas
export type { ModelLimitsTable };

/**
 * Canonical context window limits (tokens) for known models.
 * Keys are normalized lowercase substrings matched against model names.
 */
export const MODEL_LIMITS: ModelLimitsTable = {
  // Anthropic
  "claude-sonnet-4.6": 1_000_000,
  // DeepSeek
  "deepseek-v4-flash": 1_000_000,
  "deepseek-v4-pro": 1_000_000,
  // Google
  "gemini-3.1-flash-lite": 1_000_000,
  // Z.ai
  "glm-5.1": 131_072,
  // OpenAI
  "gpt-5.4-mini": 400_000,
  "gpt-5.4-nano": 400_000,
  "gpt-5.5": 1_050_000,

  // xAI
  "grok-4.3": 1_000_000,
  // Moonshot AI
  "kimi-k2.6": 262_000,
  "mimo-v2.5": 1_000_000,
  // Xiaomi
  "mimo-v2.5-pro": 1_000_000,
};

/** Default context window (tokens) when model is unknown. */
export const DEFAULT_CONTEXT_LIMIT = 128_000;

const sortedLimitKeysCache = new WeakMap<ModelLimitsTable, string[]>();

function getSortedLimitKeys(table: ModelLimitsTable): string[] {
  const cached = sortedLimitKeysCache.get(table);
  if (cached) return cached;
  const keys = Object.keys(table).sort((a, b) => b.length - a.length);
  sortedLimitKeysCache.set(table, keys);
  return keys;
}

/**
 * Resolve the context window limit for a given model.
 * Performs a lowercase substring match against known keys.
 *
 * @param modelName The model identifier (e.g., "gpt-5.5").
 * @param table Optional override table.
 * @returns Context window token limit.
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
