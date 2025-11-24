/**
 * @fileoverview Activity details API route.
 *
 * GET /api/activities/[id]
 * Retrieves detailed information for a specific activity by Google Place ID.
 */

import "server-only";

import { getActivitiesService } from "@domain/activities/container";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import { getCurrentUser } from "@/lib/supabase/factory";

const placeIdSchema = z.string().min(1);

export const GET = withApiGuards({
  auth: false, // Allow anonymous access
  rateLimit: "activities:details",
  telemetry: "activities.details",
})(async (_req, { supabase }, _body, routeContext) => {
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

  const userResult = await getCurrentUser(supabase);
  const service = getActivitiesService();

  try {
    const activity = await service.details(validated.data, {
      userId: userResult.user?.id ?? undefined,
    });

    return Response.json(activity);
  } catch (error) {
    if (error instanceof Error && error.message.includes("not found")) {
      return Response.json(
        { error: "not_found", reason: error.message },
        { status: 404 }
      );
    }
    throw error;
  }
});
