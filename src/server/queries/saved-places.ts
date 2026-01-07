/**
 * @fileoverview Server-side saved places read queries (DB access).
 */

import "server-only";

import type { SavedPlaceSnapshot } from "@schemas/places";
import { savedPlaceSnapshotSchema } from "@schemas/places";
import type { Database } from "@/lib/supabase/database.types";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";
import { normalizePlaceIdForStorage } from "@/lib/trips/actions/_shared";

const logger = createServerLogger("server.queries.saved_places");

type SavedPlaceRow = Database["public"]["Tables"]["saved_places"]["Row"];

function isPlainJsonObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

export async function listSavedPlacesForTrip(
  supabase: TypedServerSupabase,
  params: { tripId: number }
): Promise<SavedPlaceSnapshot[]> {
  const { data, error } = await supabase
    .from("saved_places")
    .select("created_at,place_id,place_snapshot")
    .eq("trip_id", params.tripId)
    .order("created_at", { ascending: false });

  if (error) {
    logger.error("saved_places_query_failed", {
      error: error.message,
      tripId: params.tripId,
    });
    throw new Error("Failed to load saved places");
  }

  const rows = (data ?? []) as Pick<
    SavedPlaceRow,
    "created_at" | "place_id" | "place_snapshot"
  >[];

  const snapshots: SavedPlaceSnapshot[] = [];
  const invalidRows: Array<{ placeId: string; issues: string[] }> = [];

  for (const row of rows) {
    const placeId = normalizePlaceIdForStorage(row.place_id);
    const snapshotJson = isPlainJsonObject(row.place_snapshot)
      ? row.place_snapshot
      : {};

    const parsed = savedPlaceSnapshotSchema.safeParse(snapshotJson);
    if (!parsed.success) {
      invalidRows.push({
        issues: parsed.error.issues.map((issue) => issue.path.join(".")),
        placeId,
      });
      continue;
    }

    const savedAt = parsed.data.savedAt ?? row.created_at ?? undefined;
    const normalized: SavedPlaceSnapshot = {
      ...parsed.data,
      place: {
        ...parsed.data.place,
        placeId,
      },
      savedAt,
    };

    const normalizedParse = savedPlaceSnapshotSchema.safeParse(normalized);
    if (normalizedParse.success) {
      snapshots.push(normalizedParse.data);
    } else {
      invalidRows.push({
        issues: normalizedParse.error.issues.map((issue) => issue.path.join(".")),
        placeId,
      });
    }
  }

  if (invalidRows.length > 0) {
    logger.warn("saved_places_row_validation_failed", {
      count: invalidRows.length,
      invalidRows,
      tripId: params.tripId,
    });
  }

  return snapshots;
}
