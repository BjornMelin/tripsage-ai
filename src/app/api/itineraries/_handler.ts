/**
 * @fileoverview Dependency-injected handlers for itinerary CRUD routes.
 */

import { itineraryItemCreateSchema } from "@schemas/trips";
import { NextResponse } from "next/server";
import { errorResponse, validateSchema } from "@/lib/api/route-helpers";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { mapItineraryItemCreateToDbInsert } from "@/lib/trips/mappers";

export interface ItinerariesDeps {
  supabase: TypedServerSupabase;
}

export async function handleListItineraryItems(
  deps: ItinerariesDeps,
  params: { userId: string; tripId?: number }
): Promise<Response> {
  let query = deps.supabase
    .from("itinerary_items")
    .select("*")
    .eq("user_id", params.userId);

  if (params.tripId !== undefined) {
    query = query.eq("trip_id", params.tripId);
  }

  const { data, error } = await query.order("start_time", { ascending: true });

  if (error) {
    return errorResponse({
      err: error,
      error: "internal",
      reason: "Failed to load itinerary items",
      status: 500,
    });
  }

  return NextResponse.json(data ?? [], { status: 200 });
}

export async function handleCreateItineraryItem(
  deps: ItinerariesDeps,
  params: { userId: string; body: unknown }
): Promise<Response> {
  const validation = validateSchema(itineraryItemCreateSchema, params.body);
  if ("error" in validation) {
    return validation.error;
  }

  const payload = validation.data;

  const { error: tripError } = await deps.supabase
    .from("trips")
    .select("id")
    .eq("id", payload.tripId)
    .eq("user_id", params.userId)
    .single();

  if (tripError) {
    // PGRST116: PostgREST error code for "no rows returned" from .single()
    if (tripError.code === "PGRST116") {
      return errorResponse({
        error: "forbidden",
        reason: "Trip not found for user",
        status: 403,
      });
    }

    return errorResponse({
      err: tripError,
      error: "internal",
      reason: "Failed to verify trip ownership",
      status: 500,
    });
  }

  const insertPayload = mapItineraryItemCreateToDbInsert(payload, params.userId);
  const { data, error } = await deps.supabase
    .from("itinerary_items")
    .insert(insertPayload)
    .select("*")
    .single();

  if (error || !data) {
    return errorResponse({
      err: error ?? new Error("Insert returned no data"),
      error: "internal",
      reason: "Failed to create itinerary item",
      status: 500,
    });
  }

  return NextResponse.json(data, { status: 201 });
}
