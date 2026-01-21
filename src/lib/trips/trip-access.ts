import "server-only";

import { errorResponse, forbiddenResponse } from "@/lib/api/route-helpers";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";

const logger = createServerLogger("trip-access");

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
    supabase
      .from("trips")
      .select("id")
      .eq("id", tripId)
      .eq("user_id", userId)
      .maybeSingle(),
    supabase
      .from("trip_collaborators")
      .select("id")
      .eq("trip_id", tripId)
      .eq("user_id", userId)
      .maybeSingle(),
  ]);

  if (ownerResult.error) {
    logger.error("trip_access_owner_check_failed", {
      error: ownerResult.error.message,
      tripId,
      userId,
    });
    return errorResponse({
      err: new Error(ownerResult.error.message),
      error: "internal",
      reason: "Failed to validate trip access",
      status: 500,
    });
  }

  // If they are the owner, they have access
  if (ownerResult.data) return null;

  if (collaboratorResult.error) {
    logger.error("trip_access_collaborator_check_failed", {
      error: collaboratorResult.error.message,
      tripId,
      userId,
    });
    return errorResponse({
      err: new Error(collaboratorResult.error.message),
      error: "internal",
      reason: "Failed to validate trip access",
      status: 500,
    });
  }

  // If they are not a collaborator, they are forbidden
  if (!collaboratorResult.data) {
    return forbiddenResponse("You do not have access to this trip");
  }

  return null;
}
