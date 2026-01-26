import "server-only";

import {
  errorResponse,
  forbiddenResponse,
  notFoundResponse,
} from "@/lib/api/route-helpers";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { getMaybeSingle } from "@/lib/supabase/typed-helpers";
import { createServerLogger } from "@/lib/telemetry/logger";

const logger = createServerLogger("trip-access");

function extractErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/**
 * Validate that a user has owner or collaborator access to a trip.
 *
 * @param options - Access check configuration
 * @param options.supabase - Authenticated Supabase client
 * @param options.tripId - The numeric identifier of the trip to check access for
 * @param options.userId - The ID of the requesting user
 * @returns An HTTP error `Response` when access is denied or a database error
 *   occurs, `null` when access is granted
 */
export async function ensureTripAccess(options: {
  supabase: TypedServerSupabase;
  tripId: number;
  userId: string;
}): Promise<Response | null> {
  const { supabase, tripId, userId } = options;

  // Run owner and collaborator checks in parallel to eliminate waterfall
  const [ownerResult, collaboratorResult] = await Promise.all([
    getMaybeSingle(
      supabase,
      "trips",
      (qb) => qb.eq("id", tripId).eq("user_id", userId),
      { select: "id", validate: false }
    ),
    getMaybeSingle(
      supabase,
      "trip_collaborators",
      (qb) => qb.eq("trip_id", tripId).eq("user_id", userId),
      { select: "id", validate: false }
    ),
  ]);

  if (ownerResult.error) {
    const message = extractErrorMessage(ownerResult.error);
    logger.error("trip_access_owner_check_failed", {
      error: message,
      tripId,
      userId,
    });
    return errorResponse({
      err: ownerResult.error,
      error: "internal",
      reason: "Failed to validate trip access",
      status: 500,
    });
  }

  // If they are the owner, they have access
  if (ownerResult.data) return null;

  if (collaboratorResult.error) {
    const message = extractErrorMessage(collaboratorResult.error);
    logger.error("trip_access_collaborator_check_failed", {
      error: message,
      tripId,
      userId,
    });
    return errorResponse({
      err: collaboratorResult.error,
      error: "internal",
      reason: "Failed to validate trip access",
      status: 500,
    });
  }

  if (collaboratorResult.data) return null;

  const { data: tripExists, error: existsError } = await getMaybeSingle(
    supabase,
    "trips",
    (qb) => qb.eq("id", tripId),
    { select: "id", validate: false }
  );

  if (existsError) {
    const message = extractErrorMessage(existsError);
    logger.error("trip_access_existence_check_failed", {
      error: message,
      tripId,
      userId,
    });
    return errorResponse({
      err: existsError,
      error: "internal",
      reason: "Failed to validate trip access",
      status: 500,
    });
  }

  if (!tripExists) {
    return notFoundResponse("Trip");
  }

  // If they are not a collaborator, they are forbidden
  return forbiddenResponse("You do not have access to this trip");
}
