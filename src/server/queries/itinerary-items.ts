/**
 * @fileoverview Server-side itinerary item read queries (DB access).
 */

import "server-only";

import type { ItineraryItem } from "@schemas/trips";
import { itineraryItemSchema, itineraryItemTypeSchema } from "@schemas/trips";
import type { Database } from "@/lib/supabase/database.types";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";

const logger = createServerLogger("server.queries.itinerary");

type ItineraryItemRow = Database["public"]["Tables"]["itinerary_items"]["Row"];

function isPlainJsonObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

export async function listItineraryItemsForTrip(
  supabase: TypedServerSupabase,
  params: { tripId: number }
): Promise<ItineraryItem[]> {
  const { data, error } = await supabase
    .from("itinerary_items")
    .select("*")
    .eq("trip_id", params.tripId)
    .order("start_time", { ascending: true });

  if (error) {
    logger.error("itinerary_items_query_failed", {
      error: error.message,
      tripId: params.tripId,
    });
    throw new Error("Failed to load itinerary items");
  }

  const rows = (data ?? []) as ItineraryItemRow[];
  const items: ItineraryItem[] = [];
  const invalidRows: Array<{ id: number; issues: string[] }> = [];

  for (const row of rows) {
    const itemTypeResult = itineraryItemTypeSchema.safeParse(row.item_type);
    if (!itemTypeResult.success) {
      invalidRows.push({
        id: row.id,
        issues: ["item_type"],
      });
      continue;
    }

    const payload = isPlainJsonObject(row.metadata) ? row.metadata : {};
    const mapped = {
      bookingStatus: row.booking_status ?? "planned",
      createdAt: row.created_at ?? undefined,
      createdBy: row.user_id,
      currency: row.currency ?? "USD",
      description: row.description ?? undefined,
      endAt: row.end_time ?? undefined,
      externalId: row.external_id ?? undefined,
      id: row.id,
      itemType: itemTypeResult.data,
      location: row.location ?? undefined,
      payload,
      price: row.price ?? undefined,
      startAt: row.start_time ?? undefined,
      title: row.title,
      tripId: row.trip_id,
      updatedAt: row.updated_at ?? undefined,
    };

    const parsed = itineraryItemSchema.safeParse(mapped);
    if (parsed.success) {
      items.push(parsed.data);
    } else {
      invalidRows.push({
        id: row.id,
        issues: parsed.error.issues.map((issue) => issue.path.join(".")),
      });
    }
  }

  if (invalidRows.length > 0) {
    logger.warn("itinerary_items_row_validation_failed", {
      count: invalidRows.length,
      invalidRows,
      tripId: params.tripId,
    });
  }

  return items;
}
