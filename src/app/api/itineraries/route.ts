/**
 * @fileoverview Itinerary items CRUD API route handlers.
 */

import "server-only";

import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, parseJsonBody, requireUserId } from "@/lib/api/route-helpers";
import { handleCreateItineraryItem, handleListItineraryItems } from "./_handler";

/**
 * GET /api/itineraries
 *
 * Returns itinerary items, optionally filtered by tripId.
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "itineraries:list",
  telemetry: "itineraries.list",
})((req, { supabase, user }) => {
  const result = requireUserId(user);
  if ("error" in result) return result.error;
  const { userId } = result;

  const tripIdParam = req.nextUrl.searchParams.get("tripId");
  let tripId: number | undefined;

  if (tripIdParam !== null) {
    const parsed = Number.parseInt(tripIdParam, 10);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      return errorResponse({
        error: "invalid_request",
        reason: "tripId must be a positive integer",
        status: 400,
      });
    }
    tripId = parsed;
  }

  return handleListItineraryItems({ supabase }, { tripId, userId });
});

/**
 * POST /api/itineraries
 *
 * Creates a new itinerary item for the authenticated user.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "itineraries:create",
  telemetry: "itineraries.create",
})(async (req, { supabase, user }) => {
  const result = requireUserId(user);
  if ("error" in result) return result.error;
  const { userId } = result;

  const parsed = await parseJsonBody(req);
  if ("error" in parsed) {
    return parsed.error;
  }

  return handleCreateItineraryItem({ supabase }, { body: parsed.body, userId });
});
