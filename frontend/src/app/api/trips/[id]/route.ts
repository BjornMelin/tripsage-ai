/**
 * @fileoverview Trip detail route handlers (GET, PUT, DELETE).
 *
 * Provides per-trip CRUD for authenticated users with cache invalidation and
 * strict validation against Supabase schemas.
 */

import "server-only";

import { tripsRowSchema, tripsUpdateSchema } from "@schemas/supabase";
import { tripUpdateSchema } from "@schemas/trips";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import type { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import {
  errorResponse,
  notFoundResponse,
  parseJsonBody,
  parseNumericId,
  requireUserId,
  validateSchema,
} from "@/lib/api/route-helpers";
import { bumpTag } from "@/lib/cache/tags";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { deleteSingle, getSingle, updateSingle } from "@/lib/supabase/typed-helpers";
import { mapDbTripToUi } from "@/lib/trips/mappers";

const TRIPS_CACHE_TAG = "trips";

/**
 * Maps validated trip update payload from camelCase API contract
 * to the database update shape expected by Supabase.
 *
 * @param payload - Validated trip update payload
 * @returns Database update object ready for Supabase
 */
function mapUpdatePayloadToDb(payload: z.infer<typeof tripUpdateSchema>) {
  const updates: Record<string, unknown> = {};

  if (payload.budget !== undefined) updates.budget = payload.budget;
  if (payload.currency !== undefined) updates.currency = payload.currency;
  if (payload.destination !== undefined) updates.destination = payload.destination;
  if (payload.endDate !== undefined) updates.end_date = payload.endDate;
  // API "preferences" maps to DB "flexibility" column
  if (payload.preferences !== undefined) updates.flexibility = payload.preferences;
  if (payload.startDate !== undefined) updates.start_date = payload.startDate;
  if (payload.status !== undefined) updates.status = payload.status;
  if (payload.tags !== undefined) updates.tags = payload.tags ?? null;
  if (payload.title !== undefined) updates.name = payload.title;
  if (payload.travelers !== undefined) updates.travelers = payload.travelers;
  if (payload.tripType !== undefined) updates.trip_type = payload.tripType;

  updates.updated_at = new Date().toISOString();

  return tripsUpdateSchema.parse(updates);
}

/**
 * Fetches a trip by ID for the authenticated user.
 *
 * @param supabase - The Supabase client instance
 * @param userId - The authenticated user ID
 * @param tripId - The numeric ID of the trip to fetch
 * @returns The trip data in UI format or an error response
 */
async function getTripById(
  supabase: TypedServerSupabase,
  userId: string,
  tripId: number
) {
  const { data, error } = await getSingle(supabase, "trips", (qb) =>
    qb.eq("id", tripId).eq("user_id", userId)
  );

  if (error) {
    const supaError = error as { code?: string };
    if (supaError.code === "PGRST116") {
      return notFoundResponse("Trip");
    }

    return errorResponse({
      err: error,
      error: "internal",
      reason: "Failed to load trip",
      status: 500,
    });
  }

  if (!data) {
    return notFoundResponse("Trip");
  }

  // Parse through schema to ensure type compatibility with mapDbTripToUi
  const row = tripsRowSchema.parse(data);
  return NextResponse.json(mapDbTripToUi(row));
}

/**
 * Updates a trip by ID for the authenticated user.
 *
 * @param req - The incoming HTTP request
 * @param supabase - The Supabase client instance
 * @param userId - The authenticated user ID
 * @param tripId - The numeric ID of the trip to update
 * @returns The updated trip data in UI format or an error response
 */
async function updateTripById(
  req: NextRequest,
  supabase: TypedServerSupabase,
  userId: string,
  tripId: number
) {
  const parsed = await parseJsonBody(req);
  if ("error" in parsed) {
    return parsed.error;
  }

  const validation = validateSchema(tripUpdateSchema, parsed.body);
  if ("error" in validation) {
    return validation.error;
  }

  const updates = mapUpdatePayloadToDb(validation.data);

  const { data, error } = await updateSingle(supabase, "trips", updates, (qb) =>
    qb.eq("id", tripId).eq("user_id", userId)
  );

  if (error || !data) {
    const supaError = error as { code?: string } | null;
    if (supaError?.code === "PGRST116") {
      return notFoundResponse("Trip");
    }

    return errorResponse({
      err: error ?? new Error("Trip update returned no row"),
      error: "internal",
      reason: "Failed to update trip",
      status: 500,
    });
  }

  await bumpTag(TRIPS_CACHE_TAG);

  // Parse through schema to ensure type compatibility with mapDbTripToUi
  const row = tripsRowSchema.parse(data);
  return NextResponse.json(mapDbTripToUi(row));
}

/**
 * Deletes a trip by ID for the authenticated user.
 *
 * @param supabase - The Supabase client instance
 * @param userId - The authenticated user ID
 * @param tripId - The numeric ID of the trip to delete
 * @returns A success response or an error response
 */
async function deleteTripById(
  supabase: TypedServerSupabase,
  userId: string,
  tripId: number
) {
  const { count, error } = await deleteSingle(supabase, "trips", (qb) =>
    qb.eq("id", tripId).eq("user_id", userId)
  );

  if (error) {
    return errorResponse({
      err: error,
      error: "internal",
      reason: "Failed to delete trip",
      status: 500,
    });
  }

  if (count === 0) {
    return notFoundResponse("Trip");
  }

  await bumpTag(TRIPS_CACHE_TAG);
  return new Response(null, { status: 204 });
}

/**
 * GET /api/trips/[id] - Fetch a trip owned by the authenticated user.
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "trips:detail",
  telemetry: "trips.detail",
})(async (_req, { supabase, user }, _data, routeContext) => {
  const userResult = requireUserId(user);
  if ("error" in userResult) return userResult.error;
  const { userId } = userResult;

  const idResult = await parseNumericId(routeContext);
  if ("error" in idResult) return idResult.error;

  return getTripById(supabase, userId, idResult.id);
});

/**
 * PUT /api/trips/[id] - Update a trip owned by the authenticated user.
 */
export const PUT = withApiGuards({
  auth: true,
  rateLimit: "trips:update",
  telemetry: "trips.update",
})(async (req, { supabase, user }, _data, routeContext) => {
  const userResult = requireUserId(user);
  if ("error" in userResult) return userResult.error;
  const { userId } = userResult;

  const idResult = await parseNumericId(routeContext);
  if ("error" in idResult) return idResult.error;

  return updateTripById(req, supabase, userId, idResult.id);
});

/**
 * DELETE /api/trips/[id] - Delete a trip owned by the authenticated user.
 */
export const DELETE = withApiGuards({
  auth: true,
  rateLimit: "trips:delete",
  telemetry: "trips.delete",
})(async (_req, { supabase, user }, _data, routeContext) => {
  const userResult = requireUserId(user);
  if ("error" in userResult) return userResult.error;
  const { userId } = userResult;

  const idResult = await parseNumericId(routeContext);
  if ("error" in idResult) return idResult.error;

  return deleteTripById(supabase, userId, idResult.id);
});
