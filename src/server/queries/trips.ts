/**
 * @fileoverview Server-side trip read queries (DB access).
 */

import "server-only";

import type { TripsRow } from "@schemas/supabase";
import { tripsRowSchema } from "@schemas/supabase";
import type { TripFilters, UiTrip } from "@schemas/trips";
import { storeTripSchema } from "@schemas/trips";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";
import { mapDbTripToUi } from "@/lib/trips/mappers";

const logger = createServerLogger("server.queries.trips");

/**
 * Escapes SQL LIKE/ILIKE wildcard characters in user input.
 */
function escapeIlikePattern(input: string): string {
  return input.replace(/\\/g, "\\\\").replace(/%/g, "\\%").replace(/_/g, "\\_");
}

export async function listTripsForUser(
  supabase: TypedServerSupabase,
  params: { currentUserId: string; filters?: TripFilters }
): Promise<UiTrip[]> {
  const filters = params.filters ?? {};

  // NOTE: This query intentionally does NOT filter by `user_id`.
  // We rely on Supabase Row Level Security (RLS) to return all trips the current
  // user is allowed to see (including collaborator access), while the
  // `currentUserId` is used only for mapping (e.g. role/permissions fields).
  //
  // Do not call this with a service-role Supabase client unless you also add
  // explicit access constraints in the query.
  let query = supabase
    .from("trips")
    .select("*")
    .order("created_at", { ascending: false });

  if (filters.destination) {
    const escapedDestination = escapeIlikePattern(filters.destination);
    query = query.ilike("destination", `%${escapedDestination}%`);
  }

  if (filters.status) {
    query = query.eq("status", filters.status);
  }

  if (filters.startDate) {
    query = query.gte("start_date", filters.startDate);
  }

  if (filters.endDate) {
    query = query.lte("end_date", filters.endDate);
  }

  const { data, error } = await query;
  if (error) {
    logger.error("trips_query_failed", { error: error.message });
    throw new Error("Failed to load trips");
  }

  const rawRows = data ?? [];
  const validRows: TripsRow[] = [];
  const failedRows: Array<{ id: unknown; issues: string[] }> = [];

  for (const row of rawRows) {
    const parsed = tripsRowSchema.safeParse(row);
    if (parsed.success) {
      validRows.push(parsed.data);
    } else {
      failedRows.push({
        id: (row as { id?: unknown }).id,
        issues: parsed.error.issues.map((issue) => issue.path.join(".")),
      });
    }
  }

  if (failedRows.length > 0) {
    logger.warn("trips_row_validation_failed", {
      count: failedRows.length,
      failedRows,
    });
  }

  const uiTrips = validRows.map((row) =>
    mapDbTripToUi(row, { currentUserId: params.currentUserId })
  );

  const validated: UiTrip[] = [];
  const invalidTrips: Array<{ id: unknown; issues: string[] }> = [];

  for (const trip of uiTrips) {
    const parsed = storeTripSchema.safeParse(trip);
    if (parsed.success) {
      validated.push(parsed.data);
    } else {
      invalidTrips.push({
        id: (trip as { id?: unknown }).id,
        issues: parsed.error.issues.map((issue) => issue.path.join(".")),
      });
    }
  }

  if (invalidTrips.length > 0) {
    logger.warn("trips_ui_validation_failed", {
      count: invalidTrips.length,
      invalidTrips,
    });
  }

  return validated;
}
