/**
 * @fileoverview Supabase-backed persistence helpers for accommodations workflows.
 */

import "server-only";

import type {
  AccommodationBookingInsert,
  TripOwnership,
} from "@domain/accommodations/types";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { getSingle, insertSingle } from "@/lib/supabase/typed-helpers";
import { createServerLogger } from "@/lib/telemetry/logger";

const logger = createServerLogger("accommodations.persistence");

/** Dependencies for accommodations persistence layer. */
export type AccommodationPersistenceDeps = {
  supabase: () => Promise<TypedServerSupabase>;
};

/** Result of persisting a booking row. */
export type PersistBookingResult = {
  error: unknown | null;
};

/**
 * Creates persistence helpers for accommodations workflows.
 *
 * @param deps - Dependencies including the Supabase client factory.
 * @returns Object with `getTripOwnership` (resolves to TripOwnership or null)
 * and `persistBooking` (resolves to PersistBookingResult).
 */
export function createAccommodationPersistence(deps: AccommodationPersistenceDeps): {
  getTripOwnership: (tripId: number, userId: string) => Promise<TripOwnership | null>;
  persistBooking: (
    bookingRow: AccommodationBookingInsert
  ) => Promise<PersistBookingResult>;
} {
  const getTripOwnership = async (
    tripId: number,
    userId: string
  ): Promise<TripOwnership | null> => {
    const supabase = await deps.supabase();
    const { data, error } = await getSingle(
      supabase,
      "trips",
      (qb) => qb.eq("id", tripId).eq("user_id", userId),
      { select: "id, user_id", validate: false }
    );
    if (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      logger.error("accommodations.trip_ownership.query_failed", {
        error: errorMessage,
        stack: error instanceof Error ? (error.stack ?? null) : null,
        tripId,
        userId,
      });
      return null;
    }
    if (!data) return null;
    return { id: data.id, userId: data.user_id };
  };

  const persistBooking = async (
    bookingRow: AccommodationBookingInsert
  ): Promise<PersistBookingResult> => {
    const supabase = await deps.supabase();
    const { error } = await insertSingle(supabase, "bookings", bookingRow, {
      select: "id",
      validate: false,
    });
    return { error: error ?? null };
  };

  return { getTripOwnership, persistBooking };
}
