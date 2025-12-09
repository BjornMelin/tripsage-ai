/**
 * @fileoverview Token counting and clamping utilities for AI SDK calls.
 * Prefers provider-reported usage where available; these helpers provide
 * fallback estimation and safe max token clamping.
 */

import type { ClampResult, TokenChatMessage } from "@schemas/tokens";
import { Tiktoken } from "js-tiktoken/lite";
import cl100kBase from "js-tiktoken/ranks/cl100k_base";
// Prefer lite ranks to avoid bundling all encodings.
// o200k_base matches modern OpenAI models (e.g., gpt-4o, gpt-5 families).
// cl100k_base covers older OpenAI models; retained as a fallback.
import o200kBase from "js-tiktoken/ranks/o200k_base";
import { getModelContextLimit } from "./limits";

/**
 * Extended Tiktoken interface with optional free method for WASM cleanup.
 */
interface TiktokenWithFree extends Tiktoken {
  free?: () => void;
}

// Re-export types from schemas (using TokenChatMessage to avoid conflict with api.ChatMessage)
export type { ClampResult };
export type ChatMessage = TokenChatMessage;

/** Heuristic fallback ratio: ~4 characters per token (UNVERIFIED for non-OpenAI). */
export const CHARS_PER_TOKEN_HEURISTIC = 4;

/** Cache for tokenizer instances to avoid repeated WASM instantiation. */
let cachedKey: "o200k" | "cl100k" | null = null;
let cachedTokenizer: Tiktoken | null = null;

/**
 * Upper bound of total characters to pass through WASM tokenizer.
 * If aggregated input exceeds this, fallback to heuristic for performance.
 */
const TOKENIZE_MAX_CHARS = 50_000;

/**
 * Select a tokenizer encoding based on model hint.
 *
 * @param modelHint Optional model identifier (e.g., "gpt-4o").
 * @returns Tiktoken instance or null if we should fallback to heuristic.
 */
function selectTokenizer(modelHint?: string): Tiktoken | null {
  const hint = (modelHint || "").toLowerCase();
  try {
    const key: typeof cachedKey =
      hint.includes("gpt-4o") || hint.includes("gpt-5")
        ? "o200k"
        : hint.includes("gpt-3.5") || hint.includes("gpt-4")
          ? "cl100k"
          : null;
    if (!key) return null;

    if (cachedTokenizer && cachedKey === key) return cachedTokenizer;

    // Dispose previous tokenizer if the WASM exposes free().
    if (cachedTokenizer && (cachedTokenizer as Tiktoken & { free?: () => void }).free) {
      (cachedTokenizer as Tiktoken & { free?: () => void }).free?.();
    }

    cachedTokenizer = new Tiktoken(key === "o200k" ? o200kBase : cl100kBase);
    cachedKey = key;
    return cachedTokenizer;
  } catch {
    return null;
  }
}

/**
 * Count tokens for an array of texts, using OpenAI-compatible tokenizer when possible.
 * If tokenizer is not available for the model, fallback to a conservative heuristic.
 *
 * @param texts Input text fragments to count.
 * @param modelHint Optional model identifier (guides tokenizer selection).
 * @returns Total token count across all texts.
 */
export function countTokens(texts: string[], modelHint?: string): number {
  if (!texts.length) return 0;
  // Heuristic fast-path when text size is very large to avoid heavy WASM work.
  let charSum = 0;
  for (const t of texts) charSum += (t || "").length;
  const oversized = charSum > TOKENIZE_MAX_CHARS;

  const enc = oversized ? null : selectTokenizer(modelHint);
  if (enc) {
    let total = 0;
    try {
      for (const t of texts) total += enc.encode(t || "").length;
    } finally {
      // Release WASM resources if available and not using the shared cache.
      const tokenizer = enc as TiktokenWithFree;
      if (enc !== cachedTokenizer && typeof tokenizer.free === "function") {
        tokenizer.free();
      }
    }
    return total;
  }
  // Heuristic fallback
  return Math.max(0, Math.ceil(charSum / CHARS_PER_TOKEN_HEURISTIC));
}

/**
 * Clamp desired max output tokens based on model context window and prompt length.
 * Counts tokens from message content fields only. System prompt is included when present.
 *
 * @param messages Chat messages to be sent to the model.
 * @param desiredMax Requested max output tokens.
 * @param modelName Model identifier; used to resolve context window.
 * @param table Optional limits override table.
 * @returns ClampResult with final maxTokens and reasons for any clamping.
 */
export function clampMaxTokens(
  messages: ChatMessage[],
  desiredMax: number,
  modelName: string | undefined,
  table?: Record<string, number>
): ClampResult {
  const reasons: string[] = [];

  // Normalize desired max
  let finalDesired = Number.isFinite(desiredMax) ? Math.floor(desiredMax) : 0;
  if (finalDesired <= 0) {
    finalDesired = 1;
    reasons.push("maxTokens_clamped_invalid_desired");
  }

  const modelLimit = getModelContextLimit(modelName, table);
  const promptTokens = countTokens(
    (messages || []).map((m) => m?.content ?? ""),
    modelName
  );

  const available = Math.max(0, modelLimit - promptTokens);
  let maxTokens = Math.min(finalDesired, available);

  if (maxTokens <= 0) {
    maxTokens = 1;
    reasons.push("maxTokens_clamped_model_limit");
  } else if (finalDesired > available) {
    reasons.push("maxTokens_clamped_model_limit");
  }

  return { maxTokens, reasons };
}

/**
 * Helper to compute prompt token count (content-only) for a message list.
 *
 * @param messages Chat messages.
 * @param modelHint Optional model hint for tokenizer selection.
 * @returns Token count of the prompt.
 */
export function countPromptTokens(messages: ChatMessage[], modelHint?: string): number {
  return countTokens(
    messages.map((m) => m?.content ?? ""),
    modelHint
  );
}
