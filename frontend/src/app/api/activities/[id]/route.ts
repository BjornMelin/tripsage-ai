/**
 * @fileoverview Activity details API route.
 *
 * GET /api/activities/[id]
 * Retrieves detailed information for a specific activity by Google Place ID.
 */

import "server-only";

import { getActivitiesService } from "@domain/activities/container";
import { isNotFoundError } from "@domain/activities/errors";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import { getCurrentUser } from "@/lib/supabase/factory";

const placeIdSchema = z.string().min(1);

/**
 * Checks if the request has authentication cookies indicating a potential authenticated user.
 *
 * @param req - Next.js request object.
 * @returns True if auth cookies are present.
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

export const GET = withApiGuards({
  auth: false, // Allow anonymous access
  rateLimit: "activities:details",
  telemetry: "activities.details",
})(async (req, { supabase }, _body, routeContext) => {
  const params = await routeContext.params;
  const placeId = params?.id;
  if (!placeId) {
    return Response.json(
      { error: "invalid_request", reason: "Place ID is required" },
      { status: 400 }
    );
  }

  const validated = placeIdSchema.safeParse(placeId);
  if (!validated.success) {
    return Response.json(
      { error: "invalid_request", reason: "Invalid Place ID format" },
      { status: 400 }
    );
  }

  // Only call getCurrentUser if auth cookies are present to avoid unnecessary Supabase calls
  let userId: string | undefined = "anon";
  if (hasAuthCookies(req)) {
    const userResult = await getCurrentUser(supabase);
    userId = userResult.user?.id ?? "anon";
  }

  const service = getActivitiesService();

  try {
    const activity = await service.details(validated.data, {
      userId,
    });

    return Response.json(activity);
  } catch (error) {
    if (isNotFoundError(error) || (error instanceof Error && /not found/i.test(error.message))) {
      return Response.json(
        { error: "not_found", reason: error.message },
        { status: 404 }
      );
    }
    throw error;
  }
});
