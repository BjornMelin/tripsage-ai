/**
 * @fileoverview Itinerary items CRUD API route handlers.
 */

"use server";

import "server-only";

import type { Json } from "@schemas/supabase";
import type { ItineraryItemCreateInput } from "@schemas/trips";
import { itineraryItemCreateSchema } from "@schemas/trips";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { createUnifiedErrorResponse } from "@/lib/api/error-response";
import { withApiGuards } from "@/lib/api/factory";
import { validateSchema } from "@/lib/next/route-helpers";
import type { Database } from "@/lib/supabase/database.types";
import type { TypedServerSupabase } from "@/lib/supabase/server";

/**
 * Maps validated itinerary item payload to Supabase itinerary_items insert shape.
 *
 * This keeps request/response validation layered on top of the generated
 * Supabase table schemas, avoiding direct coupling between API contracts and
 * database column names.
 */
function mapCreatePayloadToInsert(
  payload: ItineraryItemCreateInput,
  userId: string
): Database["public"]["Tables"]["itinerary_items"]["Insert"] {
  return {
    booking_status: payload.bookingStatus,
    currency: payload.currency,
    description: payload.description ?? null,
    end_time: payload.endTime ?? null,
    external_id: payload.externalId ?? null,
    item_type: payload.itemType,
    location: payload.location ?? null,
    metadata: (payload.metadata ?? {}) as Json,
    price: payload.price,
    start_time: payload.startTime ?? null,
    title: payload.title,
    trip_id: payload.tripId,
    user_id: userId,
  };
}

/** Creates a new itinerary item for the authenticated user. */
async function createItineraryItem(
  supabase: TypedServerSupabase,
  userId: string,
  req: NextRequest
): Promise<NextResponse> {
  const json = await req.json();
  const validation = validateSchema(itineraryItemCreateSchema, json);
  if ("error" in validation) {
    return validation.error;
  }

  if (validation.data.tripId) {
    const { data: trip, error: tripError } = await supabase
      .from("trips")
      .select("id, user_id")
      .eq("id", validation.data.tripId)
      .eq("user_id", userId)
      .single();
    if (tripError) {
      if (tripError.code === "PGRST116") {
        return createUnifiedErrorResponse({
          error: "forbidden",
          reason: "Trip not found for user",
          status: 403,
        });
      }
      return createUnifiedErrorResponse({
        err: tripError,
        error: "internal",
        reason: "Failed to verify trip ownership",
        status: 500,
      });
    }
  }

  const insertPayload = mapCreatePayloadToInsert(validation.data, userId);

  const { data, error } = await supabase
    .from("itinerary_items")
    .insert(insertPayload)
    .select("*")
    .single();
  if (error || !data) {
    return createUnifiedErrorResponse({
      err: error,
      error: "internal",
      reason: "Failed to create itinerary item",
      status: 500,
    });
  }

  return NextResponse.json(data, { status: 201 });
}

/** Lists itinerary items, optionally filtered by trip ID. */
async function listItineraryItems(
  supabase: TypedServerSupabase,
  userId: string,
  req: NextRequest
): Promise<NextResponse> {
  const url = new URL(req.url);
  const tripIdParam = url.searchParams.get("tripId");
  const tripId = tripIdParam ? Number.parseInt(tripIdParam, 10) : undefined;

  const { data: trips, error: tripsError } = await supabase
    .from("trips")
    .select("id")
    .eq("user_id", userId);
  if (tripsError) {
    return createUnifiedErrorResponse({
      err: tripsError,
      error: "internal",
      reason: "Failed to load trips",
      status: 500,
    });
  }
  const allowedTripIds = (trips ?? []).map((t) => t.id);
  if (allowedTripIds.length === 0) {
    return NextResponse.json([], { status: 200 });
  }

  let query = supabase
    .from("itinerary_items")
    .select("*")
    .in("trip_id", allowedTripIds);
  if (Number.isFinite(tripId) && allowedTripIds.includes(tripId as number)) {
    query = query.eq("trip_id", tripId as number);
  }

  const { data, error } = await query.order("start_time", { ascending: true });
  if (error) {
    return createUnifiedErrorResponse({
      err: error,
      error: "internal",
      reason: "Failed to load itinerary items",
      status: 500,
    });
  }

  return NextResponse.json(data ?? []);
}

/**
 * GET /api/itineraries
 *
 * Returns itinerary items, optionally filtered by tripId.
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "itineraries:list",
  telemetry: "itineraries.list",
})(async (req, { supabase, user }) => {
  const userId = user?.id;
  if (!userId) {
    return createUnifiedErrorResponse({
      error: "unauthorized",
      reason: "Authentication required",
      status: 401,
    });
  }
  return await listItineraryItems(supabase, userId, req);
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
  const userId = user?.id;
  if (!userId) {
    return createUnifiedErrorResponse({
      error: "unauthorized",
      reason: "Authentication required",
      status: 401,
    });
  }

  return await createItineraryItem(supabase, userId, req);
});
