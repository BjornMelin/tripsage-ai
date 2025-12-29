/**
 * @fileoverview GET /api/activities/[id] route handler.
 */

import "server-only";

import { isNotFoundError } from "@domain/activities/errors";
import type { ActivitiesCache } from "@domain/activities/service";
import { ActivitiesService } from "@domain/activities/service";
import { activitySchema } from "@schemas/search";
import { z } from "zod";
import type { RouteParamsContext } from "@/lib/api/factory";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, parseStringId } from "@/lib/api/route-helpers";
import { hashInputForCache } from "@/lib/cache/hash";
import {
  buildActivitySearchQuery,
  getActivityDetailsFromPlaces,
  searchActivitiesWithPlaces,
} from "@/lib/google/places-activities";
import { getCurrentUser } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";
import { withTelemetrySpan } from "@/lib/telemetry/span";

/**
 * Determines whether the request contains Supabase authentication cookies.
 *
 * @param req - The incoming HTTP request.
 * @returns `true` if Supabase auth cookies (`sb-access-token` or `sb-refresh-token`) are present.
 */
function hasAuthCookies(req: Request): boolean {
  const cookieHeader = req.headers.get("cookie");
  if (!cookieHeader) {
    return false;
  }
  // Check for Supabase auth cookies
  return (
    cookieHeader.includes("sb-access-token") ||
    cookieHeader.includes("sb-refresh-token")
  );
}

/**
 * GET /api/activities/[id]
 *
 * Retrieves detailed information for a specific activity by Google Place ID.
 *
 * Supports both authenticated and anonymous access. When authentication cookies
 * are present, the user ID is included in the request context for personalized
 * results.
 *
 * @param req - The incoming HTTP request.
 * @param supabase - Supabase client instance (from `withApiGuards`).
 * @param _body - Request body (unused for GET requests).
 * @param routeContext - Route context containing dynamic route parameters.
 * @returns JSON response with activity details, or an error response.
 *
 * **Response codes:**
 * - `200`: Activity found and returned.
 * - `400`: Missing or invalid Place ID.
 * - `404`: Activity not found.
 * - `429`: Rate limit exceeded.
 * - `500`: Internal server error.
 */
export const GET = withApiGuards({
  auth: false, // Allow anonymous access
  rateLimit: "activities:details",
  telemetry: "activities.details",
})(async (req, { supabase }, _body, routeContext: RouteParamsContext) => {
  const placeIdResult = await parseStringId(routeContext, "id");
  if ("error" in placeIdResult) return placeIdResult.error;
  const { id: validatedPlaceId } = placeIdResult;

  // Only call getCurrentUser if auth cookies are present to avoid unnecessary Supabase calls
  let userId: string | undefined;
  if (hasAuthCookies(req)) {
    const userResult = await getCurrentUser(supabase);
    userId = userResult.user?.id ?? undefined;
  }

  const cache: ActivitiesCache = {
    findActivityInRecentSearches: async ({ nowIso, placeId, userId }) => {
      const { data } = await supabase
        .from("search_activities")
        .select("results")
        .eq("user_id", userId)
        .gt("expires_at", nowIso)
        .order("created_at", { ascending: false })
        .limit(10);

      const rows = Array.isArray(data) ? data : [];
      for (const row of rows) {
        const parsed = z.array(activitySchema).safeParse(row.results);
        if (!parsed.success) continue;
        const match = parsed.data.find((a) => a.id === placeId);
        if (match) return match;
      }
      return null;
    },
    getSearch: async (_input) => null,
    putSearch: async (_input) => undefined,
  };

  const service = new ActivitiesService({
    cache,
    hashInput: hashInputForCache,
    logger: createServerLogger("activities.service"),
    places: {
      buildSearchQuery: buildActivitySearchQuery,
      getDetails: getActivityDetailsFromPlaces,
      search: searchActivitiesWithPlaces,
    },
    telemetry: {
      withSpan: (name, options, fn) =>
        withTelemetrySpan(name, options, async (span) => await fn(span)),
    },
  });

  try {
    const activity = await service.details(validatedPlaceId, {
      userId,
    });

    return Response.json(activity);
  } catch (error) {
    if (
      isNotFoundError(error) ||
      (error instanceof Error && /not found/i.test(error.message))
    ) {
      return errorResponse({
        err: error,
        error: "not_found",
        reason: "Activity not found",
        status: 404,
      });
    }
    throw error;
  }
});
