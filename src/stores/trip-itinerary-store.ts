/**
 * @fileoverview Zustand store for trip itinerary (destinations) state.
 *
 * Trip core fields are owned by the backend and accessed via React Query (`use-trips`).
 * This store only persists client-side itinerary/destination planning data keyed by trip id.
 */

import type { TripDestination } from "@schemas/trips";
import { create } from "zustand";
import { persist } from "zustand/middleware";

type PersistedTripStoreV0 = {
  currentTrip?: { id?: string; destinations?: TripDestination[] } | null;
  trips?: Array<{ id?: string; destinations?: TripDestination[] }>;
};

interface TripItineraryState {
  destinationsByTripId: Record<string, TripDestination[]>;

  setDestinations: (tripId: string, destinations: TripDestination[]) => void;
  addDestination: (tripId: string, destination: TripDestination) => void;
  updateDestination: (
    tripId: string,
    destinationId: string,
    update: Partial<TripDestination>
  ) => void;
  removeDestination: (tripId: string, destinationId: string) => void;
  clearTripItinerary: (tripId: string) => void;
}

export const useTripItineraryStore = create<TripItineraryState>()(
  persist(
    (set) => ({
      addDestination: (tripId, destination) =>
        set((state) => {
          const existing = state.destinationsByTripId[tripId] ?? [];
          return {
            destinationsByTripId: {
              ...state.destinationsByTripId,
              [tripId]: [...existing, destination],
            },
          };
        }),

      clearTripItinerary: (tripId) =>
        set((state) => {
          const { [tripId]: _removed, ...rest } = state.destinationsByTripId;
          return { destinationsByTripId: rest };
        }),

      destinationsByTripId: {},

      removeDestination: (tripId, destinationId) =>
        set((state) => {
          const existing = state.destinationsByTripId[tripId] ?? [];
          const next = existing.filter((dest) => dest.id !== destinationId);
          if (next.length === 0) {
            const { [tripId]: _removed, ...rest } = state.destinationsByTripId;
            return { destinationsByTripId: rest };
          }
          return {
            destinationsByTripId: { ...state.destinationsByTripId, [tripId]: next },
          };
        }),

      setDestinations: (tripId, destinations) =>
        set((state) => ({
          destinationsByTripId: {
            ...state.destinationsByTripId,
            [tripId]: destinations,
          },
        })),

      updateDestination: (tripId, destinationId, update) =>
        set((state) => {
          const existing = state.destinationsByTripId[tripId] ?? [];
          if (existing.length === 0) return state;

          const next = existing.map((dest) =>
            dest.id === destinationId ? { ...dest, ...update, id: dest.id } : dest
          );

          return {
            destinationsByTripId: { ...state.destinationsByTripId, [tripId]: next },
          };
        }),
    }),
    {
      migrate: (
        persisted,
        version
      ): Pick<TripItineraryState, "destinationsByTripId"> => {
        if (version >= 1) {
          const maybeNext = persisted as {
            destinationsByTripId?: Record<string, TripDestination[]>;
          };
          return { destinationsByTripId: maybeNext.destinationsByTripId ?? {} };
        }

        const legacy = persisted as PersistedTripStoreV0;
        const destinationsByTripId: Record<string, TripDestination[]> = {};

        const collect = (tripId?: string, destinations?: TripDestination[]) => {
          if (!tripId) return;
          if (!Array.isArray(destinations) || destinations.length === 0) return;
          destinationsByTripId[tripId] = destinations;
        };

        for (const trip of legacy.trips ?? []) {
          collect(trip?.id, trip?.destinations);
        }
        collect(legacy.currentTrip?.id, legacy.currentTrip?.destinations);

        return { destinationsByTripId };
      },
      /**
       * Use the legacy key name to preserve previously persisted trip itinerary
       * state from the former `trip-store` implementation.
       */
      name: "trip-storage",
      partialize: (state) => ({
        destinationsByTripId: state.destinationsByTripId,
      }),
      version: 1,
    }
  )
);
