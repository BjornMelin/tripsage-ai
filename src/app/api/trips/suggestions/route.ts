/**
 * @fileoverview AI-generated trip suggestions with Upstash Redis caching.
 */

import "server-only";

import { resolveProvider } from "@ai/models/registry";
import type { NextRequest } from "next/server";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, requireUserId } from "@/lib/api/route-helpers";
import { createServerLogger } from "@/lib/telemetry/logger";
import { handleTripSuggestions, type TripSuggestionsQueryParams } from "./_handler";

const MAX_BUDGET_LIMIT = 10_000_000;

const tripSuggestionsQuerySchema = z.object({
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
      error: "Category must be 50 characters or less",
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
  const logger = createServerLogger("api.trips.suggestions", {
    redactKeys: ["cacheKey"],
  });

  try {
    const result = requireUserId(user);
    if (!result.ok) return result.error;
    const userId = result.data;
    const params = parseSuggestionQueryParams(req);
    return await handleTripSuggestions(
      { logger, resolveProvider: (id, modelHint) => resolveProvider(id, modelHint) },
      { abortSignal: req.signal, params, userId }
    );
  } catch (error) {
    if (error instanceof z.ZodError) {
      return errorResponse({
        error: "invalid_request",
        issues: error.issues,
        reason: "Invalid query parameters",
        status: 400,
      });
    }
    throw error;
  }
});
