/**
 * @fileoverview Server Actions for trip planning integration.
 * Handles fetching user trips and adding activities to trips.
 */

"use server";

import "server-only";

import { type ActivitySearchParams, activitySearchParamsSchema } from "@schemas/search";
import { type TripsRow, tripsRowSchema } from "@schemas/supabase";
import {
  type ItineraryItemCreateInput,
  itineraryItemCreateSchema,
  type UiTrip,
} from "@schemas/trips";
import { z } from "zod";
import { bumpTag } from "@/lib/cache/tags";
import { createServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import { mapDbTripToUi, mapItineraryItemCreateToDbInsert } from "@/lib/trips/mappers";

const logger = createServerLogger("search.activities.actions");
const tripIdSchema = z.coerce.number().int().positive();

/**
 * Typed validation error for activity search parameters.
 * Allows callers to distinguish validation failures from other exceptions.
 */
export class ActivitySearchValidationError extends Error {
  constructor(public readonly validationMessage: string) {
    super(`Invalid activity search params: ${validationMessage}`);
    this.name = "ActivitySearchValidationError";
  }
}

/**
 * Validates/normalizes activity search parameters inside a server-side telemetry span.
 *
 * Note: this action does not execute the activity search itself.
 */
// biome-ignore lint/suspicious/useAwait: withTelemetrySpan returns a Promise synchronously
export async function submitActivitySearch(
  params: ActivitySearchParams
): Promise<ActivitySearchParams> {
  return withTelemetrySpan(
    "search.activity.server.submit",
    {
      attributes: {
        destination: params.destination,
        searchType: "activity",
      },
    },
    () => {
      const validation = activitySearchParamsSchema.safeParse(params);
      if (!validation.success) {
        throw new ActivitySearchValidationError(validation.error.message);
      }
      return validation.data;
    }
  );
}

/**
 * Fetches the authenticated user's active and planning trips.
 *
 * Retrieves trips with "planning" or "active" status from Supabase.
 * Results are mapped to the UI trip format.
 *
 * @returns A list of UI-formatted trips.
 * @throws Error if unauthorized or fetch fails.
 */
export async function getPlanningTrips(): Promise<UiTrip[]> {
  const supabase = await createServerSupabase();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    throw new Error("Unauthorized");
  }

  const { data, error } = await supabase
    .from("trips")
    .select("*")
    .eq("user_id", user.id)
    .in("status", ["planning", "active"])
    .order("created_at", { ascending: false });

  if (error) {
    logger.error("Failed to fetch trips", {
      data,
      details: error.details,
      error,
      message: error.message,
    });
    throw new Error("Failed to fetch trips");
  }

  const rows: TripsRow[] = (data ?? []).flatMap((row) => {
    const parsed = tripsRowSchema.safeParse(row);
    if (parsed.success) {
      return [parsed.data];
    }
    logger.warn("Invalid trip row skipped", {
      error: parsed.error.format(),
      tripId: (row as { id?: unknown })?.id,
    });
    return [];
  });
  return rows.map(mapDbTripToUi);
}

/**
 * Adds an activity to a specific trip.
 *
 * Validates trip ownership and activity data before inserting into Supabase.
 * Invalidates "trips" cache tag upon success.
 *
 * @param tripId - The ID of the trip to add the activity to.
 * @param activityData - The activity details including title, price, etc.
 * @throws Error if unauthorized, trip not found, or validation fails.
 */
export async function addActivityToTrip(
  tripId: number | string,
  activityData: {
    title: string;
    description?: string;
    location?: string;
    price?: number;
    currency?: string;
    startTime?: string;
    endTime?: string;
    externalId?: string;
    metadata?: Record<string, unknown>;
  }
): Promise<void> {
  const tripIdValidation = tripIdSchema.safeParse(tripId);
  if (!tripIdValidation.success) {
    throw new Error(`Invalid trip id: ${tripIdValidation.error.message}`);
  }
  const validatedTripId = tripIdValidation.data;

  const supabase = await createServerSupabase();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    throw new Error("Unauthorized");
  }

  // Validate trip ownership
  const { error: tripError } = await supabase
    .from("trips")
    .select("id")
    .eq("id", validatedTripId)
    .eq("user_id", user.id)
    .single();

  if (tripError) {
    throw new Error("Trip not found or access denied");
  }

  const payload: ItineraryItemCreateInput = {
    bookingStatus: "planned" as const,
    currency: activityData.currency ?? "USD",
    description: activityData.description,
    endTime: activityData.endTime,
    externalId: activityData.externalId,
    itemType: "activity" as const,
    location: activityData.location,
    metadata: activityData.metadata,
    price: activityData.price,
    startTime: activityData.startTime,
    title: activityData.title,
    tripId: validatedTripId,
  };

  const validation = itineraryItemCreateSchema.safeParse(payload);

  if (!validation.success) {
    logger.warn("Invalid activity data", { issues: validation.error.format() });
    throw new Error(`Invalid activity data: ${validation.error.message}`);
  }

  const insertPayload = mapItineraryItemCreateToDbInsert(validation.data, user.id);

  const { error: insertError } = await supabase
    .from("itinerary_items")
    .insert(insertPayload);

  if (insertError) {
    logger.error("Failed to add activity to trip", {
      code: insertError.code,
      details: insertError.details,
      message: insertError.message,
    });
    throw new Error(`Failed to add activity to trip: ${insertError.message}`);
  }

  try {
    await bumpTag("trips");
  } catch (cacheError) {
    logger.warn("Failed to invalidate trips cache", {
      error: cacheError instanceof Error ? cacheError.message : "unknown",
    });
  }
}
