/**
 * @fileoverview Pure handler for AI-generated trip suggestions (with caching).
 */

import "server-only";

import type { ProviderResolution } from "@schemas/providers";
import type { TripSuggestion } from "@schemas/trips";
import { tripSuggestionSchema } from "@schemas/trips";
import { generateText, Output } from "ai";
import { NextResponse } from "next/server";
import { z } from "zod";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import {
  isFilteredValue,
  sanitizeWithInjectionDetection,
} from "@/lib/security/prompt-sanitizer";

/** Cache TTL for AI suggestions (15 minutes). */
const SUGGESTIONS_CACHE_TTL_SECONDS = 900;
const MAX_BUDGET_LIMIT = 10_000_000;
const DEFAULT_SUGGESTION_LIMIT = 4;
const DEFAULT_MODEL_HINT = "gpt-4o-mini";

/**
 * Function type for resolving AI provider configurations.
 *
 * @param userId - The user ID for the request.
 * @param modelHint - An optional model hint to resolve.
 * @returns Promise resolving to a ProviderResolution.
 */
export type ProviderResolver = (
  userId: string,
  modelHint?: string
) => Promise<ProviderResolution>;

/**
 * Interface defining dependencies required for trip suggestion generation.
 */
export interface TripSuggestionsDeps {
  resolveProvider: ProviderResolver;
  logger?: {
    warn: (msg: string, meta?: Record<string, unknown>) => void;
  };
  config?: {
    cacheTtlSeconds?: number;
    modelHint?: string;
    timeoutMs?: number;
  };
}

/**
 * Request query parameters for trip suggestion generation.
 */
export interface TripSuggestionsQueryParams {
  readonly limit?: number;
  readonly budgetMax?: number;
  readonly category?: string;
}

export interface TripSuggestionsRequest {
  userId: string;
  params: TripSuggestionsQueryParams;
  abortSignal?: AbortSignal;
}

/**
 * Builds cache key for trip suggestions.
 *
 * @param userId - Authenticated user ID.
 * @param params - Query parameters.
 * @returns Redis cache key.
 */
function buildSuggestionsCacheKey(
  userId: string,
  params: TripSuggestionsQueryParams
): string {
  const canonical = canonicalizeParamsForCache(params as Record<string, unknown>);
  return `trips:suggestions:${userId}:${canonical || "default"}`;
}

/**
 * Builds a model prompt for trip suggestions based on user filters.
 *
 * @param params - Parsed query parameters.
 * @returns Prompt string for the language model.
 */
function buildSuggestionPrompt(params: TripSuggestionsQueryParams): string {
  const effectiveLimit =
    params.limit && params.limit > 0 ? params.limit : DEFAULT_SUGGESTION_LIMIT;

  const parts: string[] = [
    `Suggest ${effectiveLimit} realistic multi-day trips for a travel planning application.`,
    "Return only structured data; do not include prose outside of the JSON structure.",
  ];

  if (params.budgetMax && params.budgetMax > 0) {
    parts.push(
      `Each trip should respect an approximate budget cap of ${Math.min(
        params.budgetMax,
        MAX_BUDGET_LIMIT
      )}.`
    );
  }

  if (params.category) {
    // Sanitize category to prevent prompt injection (with injection detection)
    const safeCategory = sanitizeWithInjectionDetection(params.category, 50);
    if (safeCategory && !isFilteredValue(safeCategory)) {
      parts.push(`Focus on the "${safeCategory}" category where possible.`);
    }
  }

  parts.push(
    "Ensure destinations are diverse and include a short description, estimated price, duration in days, best time to visit, and at least three highlights."
  );

  return parts.join(" ");
}

/**
 * Generates trip suggestions, checking cache first.
 *
 * @param deps - Handler dependencies.
 * @param userId - Authenticated user ID.
 * @param params - Parsed query parameters.
 * @returns Array of trip suggestions.
 */
async function generateSuggestionsWithCache(
  deps: TripSuggestionsDeps,
  request: { abortSignal?: AbortSignal },
  userId: string,
  params: TripSuggestionsQueryParams
): Promise<TripSuggestion[]> {
  const cacheKey = buildSuggestionsCacheKey(userId, params);

  // Check cache
  const cached = await getCachedJson<TripSuggestion[]>(cacheKey, {
    namespace: "trips",
  });
  if (cached) {
    return cached;
  }

  // Generate via AI
  const prompt = buildSuggestionPrompt(params);
  const modelHint = deps.config?.modelHint ?? DEFAULT_MODEL_HINT;
  const { model, modelId } = await deps.resolveProvider(userId, modelHint);

  const controller = new AbortController();
  const timeoutMs = deps.config?.timeoutMs ?? 30_000;
  const timeout =
    timeoutMs > 0 ? setTimeout(() => controller.abort(), timeoutMs) : undefined;

  if (request.abortSignal) {
    if (request.abortSignal.aborted) {
      controller.abort();
    } else {
      request.abortSignal.addEventListener("abort", () => controller.abort(), {
        once: true,
      });
    }
  }

  let result: Awaited<ReturnType<typeof generateText>> | undefined;
  try {
    const responseSchema = z.object({
      suggestions: tripSuggestionSchema.array().nullable(),
    });
    result = await generateText({
      abortSignal: controller.signal,
      model,
      output: Output.object({ schema: responseSchema }),
      prompt,
    });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      deps.logger?.warn("trips_suggestions_generation_timed_out", {
        modelHint,
        modelId,
        timeoutMs,
      });
      return [];
    }
    throw error;
  } finally {
    if (timeout) clearTimeout(timeout);
  }

  const suggestions = result?.output?.suggestions;

  if (!Array.isArray(suggestions)) {
    deps.logger?.warn("trips_suggestions_generation_empty", {
      hasOutput: Boolean(result?.output),
      modelHint,
      modelId,
    });
    return [];
  }

  await setCachedJson(
    cacheKey,
    suggestions,
    deps.config?.cacheTtlSeconds ?? SUGGESTIONS_CACHE_TTL_SECONDS,
    { namespace: "trips" }
  );

  return suggestions;
}

/**
 * Pure handler entrypoint for suggestions.
 *
 * @param deps - Handler dependencies.
 * @param req - Normalized request object.
 */
export async function handleTripSuggestions(
  deps: TripSuggestionsDeps,
  req: TripSuggestionsRequest
): Promise<Response> {
  const suggestions = await generateSuggestionsWithCache(
    deps,
    { abortSignal: req.abortSignal },
    req.userId,
    req.params
  );
  return NextResponse.json(suggestions);
}
