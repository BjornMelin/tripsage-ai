/**
 * @fileoverview Activity details API route.
 *
 * GET /api/activities/[id]
 * Retrieves detailed information for a specific activity by Google Place ID.
 */

import "server-only";

import { getActivitiesService } from "@domain/activities/container";
import { isNotFoundError } from "@domain/activities/errors";
import type { RouteParamsContext } from "@/lib/api/factory";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, parseStringId } from "@/lib/api/route-helpers";
import { getCurrentUser } from "@/lib/supabase/factory";

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
  let userId: string | undefined = "anon";
  if (hasAuthCookies(req)) {
    const userResult = await getCurrentUser(supabase);
    userId = userResult.user?.id ?? "anon";
  }

  const service = getActivitiesService();

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
