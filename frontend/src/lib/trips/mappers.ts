/**
 * @fileoverview Canonical mapper functions for converting between database and UI trip representations.
 * Single source of truth for DB↔UI transformations.
 */

import type { TripsRow } from "@schemas/supabase";
import type { UiTrip } from "@schemas/trips";

/**
 * Maps a database trip row to UI-friendly trip object format.
 *
 * Performs transformation from database schema (snake_case, budget as number)
 * to client-side representation (camelCase, budget as number with currency sibling).
 *
 * @param row - The raw trip row from Supabase database
 * @returns UI-formatted trip object with camelCase properties
 */
export function mapDbTripToUi(row: TripsRow): UiTrip {
  return {
    budget: row.budget,
    createdAt: row.created_at ?? undefined,
    currency: row.currency,
    description: undefined,
    destination: row.destination,
    destinations: [],
    endDate: row.end_date ?? undefined,
    id: String(row.id),
    preferences: (row.flexibility as Record<string, unknown> | undefined) ?? undefined,
    startDate: row.start_date ?? undefined,
    status: row.status,
    tags: row.notes ?? undefined,
    title: row.name,
    travelers: row.travelers,
    tripType: row.trip_type,
    updatedAt: row.updated_at ?? undefined,
    userId: row.user_id,
    visibility: "private",
  };
}
