/**
 * @fileoverview AI-generated trip suggestions API route handler.
 */

"use server";

import "server-only";

import { generateObject } from "ai";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import { resolveProvider } from "@/lib/providers/registry";
import type { TripSuggestion } from "@/lib/schemas/trips";
import { tripSuggestionSchema } from "@/lib/schemas/trips";

/**
 * Request query parameters for trip suggestion generation.
 *
 * @property limit - Maximum number of suggestions to return.
 * @property budgetMax - Optional maximum budget constraint.
 * @property category - Optional category filter.
 */
interface TripSuggestionsQueryParams {
  readonly limit?: number;
  readonly budgetMax?: number;
  readonly category?: string;
}

/**
 * Parses query-string parameters into a normalized suggestion input object.
 *
 * @param req Next.js request object for this route.
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
 * @param params Parsed query parameters.
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
 * Generates trip suggestions using the configured AI provider and TripSuggestion schema.
 *
 * @param req Next.js request object.
 * @param userId Authenticated user identifier for provider resolution.
 * @returns JSON response containing an array of TripSuggestion objects.
 */
async function generateSuggestions(
  req: NextRequest,
  userId: string
): Promise<NextResponse> {
  const params = parseSuggestionQueryParams(req);
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

  const suggestions: TripSuggestion[] = result.object?.suggestions ?? [];
  return NextResponse.json(suggestions);
}

/**
 * GET /api/trips/suggestions
 *
 * Returns AI-generated trip suggestions for the authenticated user. The
 * response is a JSON array of {@link TripSuggestion} objects validated via
 * Zod and generated with AI SDK v6 structured outputs.
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "trips:suggestions",
  telemetry: "trips.suggestions",
})((req, { user }) => {
  const userId = user?.id;
  if (!userId) {
    return NextResponse.json(
      { error: "unauthorized", reason: "Authentication required" },
      { status: 401 }
    );
  }

  return generateSuggestions(req, userId);
});
