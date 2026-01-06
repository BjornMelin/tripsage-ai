/**
 * @fileoverview Zustand store for trip itinerary (destinations) state.
 */

"use client";

import { type TripDestination, tripDestinationSchema } from "@schemas/trips";
import { z } from "zod";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import { createStoreLogger } from "@/lib/telemetry/store-logger";

const logger = createStoreLogger({ storeName: "trip-itinerary" });

const PERSISTED_V1_SCHEMA = z.strictObject({
  destinationsByTripId: z.record(z.string(), z.array(tripDestinationSchema)),
});

const LEGACY_TRIP_SCHEMA = z.strictObject({
  destinations: z.array(tripDestinationSchema).optional(),
  id: z.string().optional(),
});

const PERSISTED_V0_SCHEMA = z.strictObject({
  currentTrip: LEGACY_TRIP_SCHEMA.nullable().optional(),
  trips: z.array(LEGACY_TRIP_SCHEMA).optional(),
});

type PersistedTripStoreV0 = z.infer<typeof PERSISTED_V0_SCHEMA>;

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
  devtools(
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
            const destinationsByTripId = { ...state.destinationsByTripId };
            delete destinationsByTripId[tripId];
            return { destinationsByTripId };
          }),
        destinationsByTripId: {},

        removeDestination: (tripId, destinationId) =>
          set((state) => {
            const existing = state.destinationsByTripId[tripId] ?? [];
            const next = existing.filter((dest) => dest.id !== destinationId);
            if (next.length === 0) {
              const destinationsByTripId = { ...state.destinationsByTripId };
              delete destinationsByTripId[tripId];
              return { destinationsByTripId };
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
          persisted: unknown,
          version: number
        ): Pick<TripItineraryState, "destinationsByTripId"> => {
          try {
            if (version >= 1) {
              const parsed = PERSISTED_V1_SCHEMA.safeParse(persisted);
              if (!parsed.success) {
                logger.error("migration validation failed", {
                  error: parsed.error,
                  version,
                });
                return { destinationsByTripId: {} };
              }

              const { destinationsByTripId } = parsed.data;
              logger.info("migration succeeded", {
                keyCount: Object.keys(destinationsByTripId).length,
                version,
              });
              return { destinationsByTripId };
            }

            const parsedLegacy = PERSISTED_V0_SCHEMA.safeParse(persisted);
            if (!parsedLegacy.success) {
              logger.error("migration validation failed", {
                error: parsedLegacy.error,
                version,
              });
              return { destinationsByTripId: {} };
            }

            const legacy: PersistedTripStoreV0 = parsedLegacy.data;
            const destinationsByTripId: Record<string, TripDestination[]> = {};

            const collect = (tripId?: string, destinations?: TripDestination[]) => {
              if (!tripId) return;
              if (!destinations?.length) return;
              destinationsByTripId[tripId] = destinations;
            };

            for (const trip of legacy.trips ?? []) {
              collect(trip?.id, trip?.destinations);
            }
            collect(legacy.currentTrip?.id, legacy.currentTrip?.destinations);

            logger.info("migration succeeded", {
              keyCount: Object.keys(destinationsByTripId).length,
              version,
            });

            return { destinationsByTripId };
          } catch (error) {
            logger.error("migration failed", { error, version });
            return { destinationsByTripId: {} };
          }
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
    ),
    { name: "trip-itinerary" }
  )
);

const EMPTY_DESTINATIONS: TripDestination[] = [];

/**
 * Returns the destinations for a specific trip ID.
 * @param tripId Trip identifier.
 * @returns Destinations list (empty array when none exist).
 */
export const useDestinationsForTrip = (tripId: string): TripDestination[] =>
  useTripItineraryStore(
    (state) => state.destinationsByTripId[tripId] ?? EMPTY_DESTINATIONS
  );

/**
 * Returns whether a trip has any destinations.
 * @param tripId Trip identifier.
 * @returns True when at least one destination exists, otherwise false.
 */
export const useHasTripDestinations = (tripId: string): boolean =>
  useTripItineraryStore(
    (state) => (state.destinationsByTripId[tripId]?.length ?? 0) > 0
  );

/**
 * Returns the number of destinations for a trip.
 * @param tripId Trip identifier.
 * @returns Destination count (0 when none exist).
 */
export const useTripDestinationCount = (tripId: string): number =>
  useTripItineraryStore((state) => state.destinationsByTripId[tripId]?.length ?? 0);
