/**
 * @fileoverview Trip detail route handlers (GET, PUT, DELETE).
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
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { deleteSingle, getSingle, updateSingle } from "@/lib/supabase/typed-helpers";
import { mapDbTripToUi } from "@/lib/trips/mappers";
import { invalidateTripAccessCaches, invalidateUserTripsCache } from "../_handler";

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

function isPermissionDeniedError(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;
  const maybe = error as { code?: unknown; details?: unknown; message?: unknown };

  const code = typeof maybe.code === "string" ? maybe.code : null;
  if (code === "42501") return true;

  const details = typeof maybe.details === "string" ? maybe.details : "";
  const message = typeof maybe.message === "string" ? maybe.message : "";
  const combined = `${message} ${details}`.toLowerCase();
  return (
    combined.includes("permission denied") ||
    combined.includes("row-level security") ||
    combined.includes("violates row-level security")
  );
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
    qb.eq("id", tripId)
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
  return NextResponse.json(mapDbTripToUi(row, { currentUserId: userId }));
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
    qb.eq("id", tripId)
  );

  if (error || !data) {
    const supaError = error as { code?: string } | null;
    if (supaError?.code === "PGRST116") {
      return notFoundResponse("Trip");
    }

    if (error && isPermissionDeniedError(error)) {
      return errorResponse({
        err: error,
        error: "forbidden",
        reason: "You do not have permission to update this trip",
        status: 403,
      });
    }

    if (!error && !data) {
      const { data: existing, error: accessError } = await supabase
        .from("trips")
        .select("id")
        .eq("id", tripId)
        .maybeSingle();

      if (accessError) {
        return errorResponse({
          err: accessError,
          error: "internal",
          reason: "Failed to validate trip access",
          status: 500,
        });
      }

      if (!existing) {
        return notFoundResponse("Trip");
      }

      return errorResponse({
        error: "forbidden",
        reason: "You do not have permission to update this trip",
        status: 403,
      });
    }

    return errorResponse({
      err: error ?? new Error("Trip update returned no row"),
      error: "internal",
      reason: "Failed to update trip",
      status: 500,
    });
  }

  // Parse through schema to ensure type compatibility with mapDbTripToUi
  const row = tripsRowSchema.parse(data);
  await invalidateTripAccessCaches(supabase, tripId, row.user_id);
  return NextResponse.json(mapDbTripToUi(row, { currentUserId: userId }));
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
  const { data: trip, error: tripError } = await supabase
    .from("trips")
    .select("user_id")
    .eq("id", tripId)
    .maybeSingle();

  if (tripError) {
    return errorResponse({
      err: tripError,
      error: "internal",
      reason: "Failed to load trip",
      status: 500,
    });
  }

  if (!trip) {
    return notFoundResponse("Trip");
  }

  if (trip.user_id !== userId) {
    return errorResponse({
      error: "forbidden",
      reason: "Only the trip owner can delete this trip",
      status: 403,
    });
  }

  const { data: collaborators, error: collaboratorError } = await supabase
    .from("trip_collaborators")
    .select("user_id")
    .eq("trip_id", tripId);

  if (collaboratorError) {
    return errorResponse({
      err: collaboratorError,
      error: "internal",
      reason: "Failed to load trip collaborators",
      status: 500,
    });
  }

  const userIdsToInvalidate = new Set<string>([
    trip.user_id,
    ...(collaborators ?? [])
      .map((row) => row.user_id)
      .filter((id): id is string => typeof id === "string" && id.length > 0),
  ]);

  const { count, error } = await deleteSingle(supabase, "trips", (qb) =>
    qb.eq("id", tripId)
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

  await Promise.all(
    [...userIdsToInvalidate].map((targetUserId) =>
      invalidateUserTripsCache(targetUserId)
    )
  );
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
