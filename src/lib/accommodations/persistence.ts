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

export type AccommodationPersistenceDeps = {
  supabase: () => Promise<TypedServerSupabase>;
};

export type PersistBookingResult = {
  error: unknown | null;
};

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
    if (error || !data) return null;
    return { id: data.id, userId: data.user_id };
  };

  const persistBooking = async (
    bookingRow: AccommodationBookingInsert
  ): Promise<PersistBookingResult> => {
    const supabase = await deps.supabase();
    const { error } = await insertSingle(supabase, "bookings", bookingRow);
    return { error: error ?? null };
  };

  return { getTripOwnership, persistBooking };
}
