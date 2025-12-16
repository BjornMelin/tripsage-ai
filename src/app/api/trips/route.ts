/**
 * @fileoverview Trip CRUD API route handlers.
 */

import "server-only";

import { tripCreateSchema, tripFiltersSchema } from "@schemas/trips";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, parseJsonBody, requireUserId } from "@/lib/api/route-helpers";
import { handleCreateTrip, handleListTrips } from "./_handler";

/**
 * GET /api/trips
 *
 * Returns the authenticated user's trips filtered by optional query params.
 * Response cached in Redis with 5-minute TTL.
 *
 * @param req - NextRequest object.
 * @param supabase - Supabase client.
 * @param user - Authenticated user.
 * @returns NextResponse object.
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "trips:list",
  telemetry: "trips.list",
})(async (req, { supabase, user }) => {
  const result = requireUserId(user);
  if ("error" in result) return result.error;
  const { userId } = result;

  const url = new URL(req.url);
  const filtersParse = tripFiltersSchema.safeParse({
    destination: url.searchParams.get("destination") ?? undefined,
    endDate: url.searchParams.get("endDate") ?? undefined,
    startDate: url.searchParams.get("startDate") ?? undefined,
    status: url.searchParams.get("status") ?? undefined,
  });

  if (!filtersParse.success) {
    return errorResponse({
      err: filtersParse.error,
      error: "invalid_request",
      issues: filtersParse.error.issues,
      reason: "Invalid trip filter parameters",
      status: 400,
    });
  }

  return await handleListTrips({ supabase }, { filters: filtersParse.data, userId });
});

/**
 * POST /api/trips
 *
 * Creates a new trip owned by the authenticated user.
 * Invalidates trips cache on success.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "trips:create",
  telemetry: "trips.create",
})(async (req, { supabase, user }) => {
  const result = requireUserId(user);
  if ("error" in result) return result.error;
  const { userId } = result;

  const parsed = await parseJsonBody(req);
  if ("error" in parsed) return parsed.error;

  const validated = tripCreateSchema.safeParse(parsed.body);
  if (!validated.success) {
    return errorResponse({
      err: validated.error,
      error: "invalid_request",
      issues: validated.error.issues,
      reason: "Trip payload validation failed",
      status: 400,
    });
  }

  return await handleCreateTrip({ supabase }, { payload: validated.data, userId });
});
