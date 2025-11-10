/**
 * @fileoverview Model context window limits (in tokens) and helpers.
 * Maintains per-model context limits for safe clamping in AI SDK calls.
 */

export type ModelLimitsTable = Record<string, number>;

/**
 * Canonical context window limits (tokens) for known models.
 * Keys are normalized lowercase substrings matched against model names.
 */
export const MODEL_LIMITS: ModelLimitsTable = {
  "claude-3.5-haiku": 200_000,

  // Anthropic
  "claude-3.5-sonnet": 200_000,
  "gpt-4o": 128_000,
  "gpt-4o-mini": 128_000,
  // OpenAI
  "gpt-5": 200_000,
  "gpt-5-mini": 200_000,

  // xAI (conservative default unless provider docs specify higher)
  grok: 128_000,
};

/** Default context window (tokens) when model is unknown. */
export const DEFAULT_CONTEXT_LIMIT = 128_000;

/**
 * Resolve the context window limit for a given model.
 * Performs a lowercase substring match against known keys.
 *
 * @param modelName The model identifier (e.g., "gpt-4o").
 * @param table Optional override table.
 * @returns Context window token limit.
 */
export function getModelContextLimit(
  modelName: string | undefined,
  table: ModelLimitsTable = MODEL_LIMITS
): number {
  if (!modelName) return DEFAULT_CONTEXT_LIMIT;
  const name = modelName.toLowerCase();
  for (const key of Object.keys(table)) {
    if (name.includes(key)) return table[key];
  }
  return DEFAULT_CONTEXT_LIMIT;
}
