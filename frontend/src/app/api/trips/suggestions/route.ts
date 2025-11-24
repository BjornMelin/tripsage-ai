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
import { generateObject } from "ai";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";

/** Cache TTL for AI suggestions (15 minutes). */
const SUGGESTIONS_CACHE_TTL = 900;

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
  const limitRaw = url.searchParams.get("limit");
  const budgetRaw = url.searchParams.get("budget_max");
  const category = url.searchParams.get("category") ?? undefined;

  const limit = limitRaw ? Number.parseInt(limitRaw, 10) : undefined;
  const budgetMax = budgetRaw ? Number.parseFloat(budgetRaw) : undefined;

  return {
    budgetMax: Number.isFinite(budgetMax) ? (budgetMax as number) : undefined,
    category,
    limit: Number.isFinite(limit) ? (limit as number) : undefined,
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
    parts.push(`Focus on the '${params.category}' category where possible.`);
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

  const responseSchema = z.object({
    suggestions: tripSuggestionSchema.array().nullable(),
  });

  const result = await generateObject({
    model,
    prompt,
    schema: responseSchema,
  });

  const suggestions = result.object?.suggestions ?? [];

  // Cache result
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
  const userId = user?.id;
  if (!userId) {
    return NextResponse.json(
      { error: "unauthorized", reason: "Authentication required" },
      { status: 401 }
    );
  }

  const params = parseSuggestionQueryParams(req);
  const suggestions = await generateSuggestionsWithCache(userId, params);
  return NextResponse.json(suggestions);
});
