/**
 * @fileoverview Dependency-injected handlers for itinerary CRUD routes.
 */

import { itineraryItemCreateSchema } from "@schemas/trips";
import { NextResponse } from "next/server";
import { errorResponse, validateSchema } from "@/lib/api/route-helpers";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import type { ServerLogger } from "@/lib/telemetry/logger";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import { mapItineraryItemCreateToDbInsert } from "@/lib/trips/mappers";

export interface ItinerariesDeps {
  logger: ServerLogger;
  supabase: TypedServerSupabase;
}

export function handleListItineraryItems(
  deps: ItinerariesDeps,
  params: { userId: string; tripId?: number }
): Promise<Response> {
  return withTelemetrySpan(
    "itineraries.list.query",
    { attributes: { userId: params.userId } },
    async (span) => {
      span.setAttribute("itinerary.userId", params.userId);
      if (params.tripId !== undefined) {
        span.setAttribute("itinerary.tripId", params.tripId);
      }

      let query = deps.supabase
        .from("itinerary_items")
        .select("*")
        .eq("user_id", params.userId);

      if (params.tripId !== undefined) {
        query = query.eq("trip_id", params.tripId);
      }

      const { data, error } = await query.order("start_time", { ascending: true });

      if (error) {
        span.setAttribute("itinerary.list.error", true);
        deps.logger.error("itinerary_items_query_failed", {
          error: error.message,
          tripId: params.tripId,
          userId: params.userId,
        });
        return errorResponse({
          err: error,
          error: "internal",
          reason: "Failed to load itinerary items",
          status: 500,
        });
      }

      return NextResponse.json(data ?? [], { status: 200 });
    }
  );
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

  return await withTelemetrySpan(
    "itineraries.create.db",
    { attributes: { tripId: payload.tripId, userId: params.userId } },
    async (span) => {
      span.setAttribute("itinerary.tripId", payload.tripId);
      span.setAttribute("itinerary.userId", params.userId);

      const { error: tripError } = await deps.supabase
        .from("trips")
        .select("id")
        .eq("id", payload.tripId)
        .eq("user_id", params.userId)
        .single();

      if (tripError) {
        // PGRST116: PostgREST error code for "no rows returned" from .single()
        if (tripError.code === "PGRST116") {
          deps.logger.warn("trip_not_found_for_user", {
            tripId: payload.tripId,
            userId: params.userId,
          });
          return errorResponse({
            error: "forbidden",
            reason: "Trip not found for user",
            status: 403,
          });
        }

        span.setAttribute("itinerary.create.error", true);
        deps.logger.error("trip_lookup_failed", {
          error: tripError.message,
          tripId: payload.tripId,
          userId: params.userId,
        });
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
        span.setAttribute("itinerary.create.error", true);
        deps.logger.error("itinerary_item_insert_failed", {
          error: error?.message ?? "Insert returned no data",
          tripId: payload.tripId,
          userId: params.userId,
        });
        return errorResponse({
          err: error ?? new Error("Insert returned no data"),
          error: "internal",
          reason: "Failed to create itinerary item",
          status: 500,
        });
      }

      deps.logger.info("itinerary_item_created", {
        itemId: data.id,
        tripId: payload.tripId,
        userId: params.userId,
      });

      return NextResponse.json(data, { status: 201 });
    }
  );
}
