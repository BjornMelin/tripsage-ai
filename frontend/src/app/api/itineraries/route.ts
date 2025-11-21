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
  _userId: string
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

  const insertPayload = mapCreatePayloadToInsert(validation.data, userId);

  const { data, error } = await supabase
    .from("itinerary_items")
    .insert(insertPayload)
    .select("*")
    .single();
  if (error || !data) {
    return NextResponse.json(
      { error: "Failed to create itinerary item" },
      { status: 500 }
    );
  }

  return NextResponse.json(data, { status: 201 });
}

/** Lists itinerary items, optionally filtered by trip ID. */
async function listItineraryItems(
  supabase: TypedServerSupabase,
  req: NextRequest
): Promise<NextResponse> {
  const url = new URL(req.url);
  const tripIdParam = url.searchParams.get("tripId");
  const tripId = tripIdParam ? Number.parseInt(tripIdParam, 10) : undefined;

  let query = supabase.from("itinerary_items").select("*");
  if (Number.isFinite(tripId)) {
    query = query.eq("trip_id", tripId as number);
  }

  const { data, error } = await query.order("start_time", { ascending: true });
  if (error) {
    return NextResponse.json(
      { error: "Failed to load itinerary items" },
      { status: 500 }
    );
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
})((req, { supabase }) => listItineraryItems(supabase, req));

/**
 * POST /api/itineraries
 *
 * Creates a new itinerary item for the authenticated user.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "itineraries:create",
  telemetry: "itineraries.create",
})((req, { supabase, user }) => {
  const userId = user?.id;
  if (!userId) {
    return NextResponse.json(
      { error: "unauthorized", reason: "Authentication required" },
      { status: 401 }
    );
  }

  return createItineraryItem(supabase, userId, req);
});
