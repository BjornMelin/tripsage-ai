/**
 * @fileoverview AI-generated trip suggestions with Upstash Redis caching.
 *
 * Generates trip suggestions using AI SDK v6 structured outputs.
 * Results cached per-user in Redis with 15-minute TTL to reduce
 * redundant AI calls while maintaining freshness.
 */

import "server-only";

import { resolveProvider } from "@ai/models/registry";
import type { TripSuggestion } from "@schemas/trips";
import { tripSuggestionSchema } from "@schemas/trips";
import { generateText, Output } from "ai";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import { requireUserId } from "@/lib/api/route-helpers";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";
import {
  isFilteredValue,
  sanitizeWithInjectionDetection,
} from "@/lib/security/prompt-sanitizer";
import { createServerLogger } from "@/lib/telemetry/logger";

/** Cache TTL for AI suggestions (15 minutes). */
const SUGGESTIONS_CACHE_TTL = 900;
const MAX_BUDGET_LIMIT = 10_000_000;

const logger = createServerLogger("api.trips.suggestions");

const tripSuggestionsQuerySchema = z.strictObject({
  budget_max: z
    .string()
    .optional()
    .transform((val) => {
      if (!val) return undefined;
      const normalized = val.normalize("NFKC").trim();
      const parsed = Number.parseFloat(normalized);
      return Number.isFinite(parsed) && parsed > 0 && parsed <= MAX_BUDGET_LIMIT
        ? parsed
        : undefined;
    }),
  category: z
    .string()
    .optional()
    .transform((val) => {
      if (!val) return undefined;
      const normalized = val.normalize("NFKC").trim();
      return normalized.length > 0 ? normalized : undefined;
    })
    .refine((val) => !val || val.length <= 50, {
      message: "Category must be 50 characters or less",
    }),
  limit: z
    .string()
    .optional()
    .transform((val) => {
      if (!val) return undefined;
      const normalized = val.normalize("NFKC").trim();
      const parsed = Number.parseInt(normalized, 10);
      if (!Number.isFinite(parsed) || parsed <= 0) return undefined;
      return Math.min(parsed, 10);
    }),
});

/**
 * Request query parameters for trip suggestion generation.
 */
interface TripSuggestionsQueryParams {
  readonly limit?: number;
  readonly budgetMax?: number;
  readonly category?: string;
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
 * Parses query-string parameters into a normalized suggestion input object.
 *
 * @param req - Next.js request object for this route.
 * @returns Parsed query parameter object.
 */
function parseSuggestionQueryParams(req: NextRequest): TripSuggestionsQueryParams {
  const url = new URL(req.url);
  const parsed = tripSuggestionsQuerySchema.parse(Object.fromEntries(url.searchParams));
  return {
    budgetMax: parsed.budget_max,
    category: parsed.category,
    limit: parsed.limit,
  };
}

/**
 * Builds a model prompt for trip suggestions based on user filters.
 *
 * @param params - Parsed query parameters.
 * @returns Prompt string for the language model.
 */
function buildSuggestionPrompt(params: TripSuggestionsQueryParams): string {
  const effectiveLimit = params.limit && params.limit > 0 ? params.limit : 4;

  const parts: string[] = [
    `Suggest ${effectiveLimit} realistic multi-day trips for a travel planning application.`,
    "Return only structured data; do not include prose outside of the JSON structure.",
  ];

  if (params.budgetMax && params.budgetMax > 0) {
    parts.push(
      `Each trip should respect an approximate budget cap of ${params.budgetMax}.`
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
 * @param userId - Authenticated user ID.
 * @param params - Parsed query parameters.
 * @returns Array of trip suggestions.
 */
async function generateSuggestionsWithCache(
  userId: string,
  params: TripSuggestionsQueryParams
): Promise<TripSuggestion[]> {
  const cacheKey = buildSuggestionsCacheKey(userId, params);

  // Check cache
  const cached = await getCachedJson<TripSuggestion[]>(cacheKey);
  if (cached) {
    return cached;
  }

  // Generate via AI
  const prompt = buildSuggestionPrompt(params);
  const { model } = await resolveProvider(userId, "gpt-4o-mini");

  const responseSchema = z.strictObject({
    suggestions: tripSuggestionSchema.array().nullable(),
  });

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30_000);

  let result: Awaited<ReturnType<typeof generateText>> | undefined;
  try {
    result = await generateText({
      abortSignal: controller.signal,
      model,
      output: Output.object({ schema: responseSchema }),
      prompt,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      logger.warn("AI generation timed out", { cacheKey });
      return [];
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }

  const suggestions = result?.output?.suggestions;

  if (!Array.isArray(suggestions)) {
    logger.warn("Model returned no suggestions", {
      hasOutput: Boolean(result.output),
      keys: result.output ? Object.keys(result.output) : [],
    });
    return [];
  }

  await setCachedJson(cacheKey, suggestions, SUGGESTIONS_CACHE_TTL);

  return suggestions;
}

/**
 * GET /api/trips/suggestions
 *
 * Returns AI-generated trip suggestions for the authenticated user.
 * Response cached in Redis with 15-minute TTL.
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "trips:suggestions",
  telemetry: "trips.suggestions",
})(async (req, { user }) => {
  try {
    const result = requireUserId(user);
    if ("error" in result) return result.error;
    const { userId } = result;
    const params = parseSuggestionQueryParams(req);
    const suggestions = await generateSuggestionsWithCache(userId, params);
    return NextResponse.json(suggestions);
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { details: error.issues, error: "Invalid query parameters" },
        { status: 400 }
      );
    }
    throw error;
  }
});
