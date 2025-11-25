/**
 * @fileoverview Trip store using Zustand for managing trip state, including CRUD operations,
 * destination management, budget tracking, and persistence with local storage.
 */

import type { TripsUpdate } from "@schemas/supabase";
import type { TripDestination, UiTrip } from "@schemas/trips";
import { storeTripSchema } from "@schemas/trips";
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { secureUuid } from "@/lib/security/random";
import type { Json } from "@/lib/supabase/database.types";

/** Trip type for the store - uses canonical schema from @schemas/trips. */
export type Trip = UiTrip;

/** Destination type for the store - uses canonical schema from @schemas/trips. */
export type Destination = TripDestination;

interface TripState {
  trips: Trip[];
  currentTrip: Trip | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  setTrips: (trips: Trip[]) => void;
  setCurrentTrip: (trip: Trip | null) => void;
  loadTrips: () => Promise<void>;
  createTrip: (data: Partial<Trip>) => Promise<void>;
  updateTrip: (id: string, data: Partial<Trip>) => Promise<void>;
  deleteTrip: (id: string) => Promise<void>;
  addDestination: (tripId: string, destination: Destination) => Promise<void>;
  updateDestination: (
    tripId: string,
    destinationId: string,
    data: Partial<Destination>
  ) => Promise<void>;
  removeDestination: (tripId: string, destinationId: string) => Promise<void>;
  clearError: () => void;
}

/**
 * Zustand store hook for managing trip state with persistence.
 *
 * Provides CRUD operations for trips, destination management, budget tracking,
 * and state persistence. All operations are asynchronous and handle error states.
 *
 * @returns The trip store hook with state and actions.
 */
export const useTripStore = create<TripState>()(
  persist(
    (set, _get) => ({
      addDestination: async (tripId, destination) => {
        set({ error: null, isLoading: true });

        try {
          // This will be replaced with actual API call
          await new Promise((resolve) => setTimeout(resolve, 1000));

          const newDestination: Destination = {
            ...destination,
            id: destination.id || secureUuid(),
          };

          set((state) => {
            const trips = state.trips.map((trip) => {
              if (trip.id === tripId) {
                return {
                  ...trip,
                  destinations: [...trip.destinations, newDestination],
                  updatedAt: new Date().toISOString(),
                };
              }
              return trip;
            });

            const currentTrip =
              state.currentTrip?.id === tripId
                ? {
                    ...state.currentTrip,
                    destinations: [...state.currentTrip.destinations, newDestination],
                    updatedAt: new Date().toISOString(),
                  }
                : state.currentTrip;

            return { currentTrip, isLoading: false, trips };
          });
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : "Failed to add destination",
            isLoading: false,
          });
        }
      },

      clearError: () => set({ error: null }),

      createTrip: async (data) => {
        set({ error: null, isLoading: true });

        try {
          // Import hook will need to be used in component that calls this
          // For now, we'll use the supabase client directly
          const { createTrip: repoCreateTrip } = await import(
            "@/lib/repositories/trips-repo"
          );

          // Validate input data
          const validated = storeTripSchema.safeParse({
            ...data,
            id: secureUuid(),
            status: data.status ?? "planning",
            title: data.title ?? "Untitled Trip",
            visibility: data.visibility ?? "private",
          });

          if (!validated.success) {
            throw new Error(
              `Invalid trip data: ${validated.error.issues.map((i) => i.message).join(", ")}`
            );
          }

          const tripData = validated.data;

          const ownerId = tripData.userId ?? _get().currentTrip?.userId ?? secureUuid();

          const created = await repoCreateTrip({
            budget: tripData.budget ?? 0,
            destination: tripData.destination ?? "",
            // biome-ignore lint/style/useNamingConvention: Database API requires snake_case
            end_date: tripData.endDate ?? new Date().toISOString(),
            flexibility: (tripData.preferences ?? {}) as Json,
            name: tripData.title,
            notes: tripData.tags ?? [],
            // biome-ignore lint/style/useNamingConvention: Database API requires snake_case
            search_metadata: {},
            // biome-ignore lint/style/useNamingConvention: Database API requires snake_case
            start_date: tripData.startDate ?? new Date().toISOString(),
            travelers: tripData.travelers ?? 1,
            // biome-ignore lint/style/useNamingConvention: Database API requires snake_case
            user_id: ownerId,
          });

          // Convert to frontend format using mapper
          const frontendTrip: Trip = created;

          set((state) => ({
            currentTrip: frontendTrip,
            isLoading: false,
            trips: [...state.trips, frontendTrip],
          }));
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : "Failed to create trip",
            isLoading: false,
          });
        }
      },
      currentTrip: null,

      deleteTrip: async (id) => {
        set({ error: null, isLoading: true });

        try {
          const { deleteTrip: repoDeleteTrip } = await import(
            "@/lib/repositories/trips-repo"
          );
          const ownerId =
            _get().trips.find((trip) => trip.id === id)?.userId ??
            _get().currentTrip?.userId ??
            undefined;
          await repoDeleteTrip(Number.parseInt(id, 10), ownerId);

          set((state) => {
            const trips = state.trips.filter((trip) => trip.id !== id);
            const currentTrip = state.currentTrip?.id === id ? null : state.currentTrip;

            return { currentTrip, isLoading: false, trips };
          });
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : "Failed to delete trip",
            isLoading: false,
          });
        }
      },
      error: null,
      isLoading: false,

      loadTrips: async () => {
        set({ error: null, isLoading: true });

        try {
          const { listTrips } = await import("@/lib/repositories/trips-repo");
          const frontendTrips = await listTrips();
          set({ isLoading: false, trips: frontendTrips });
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : "Failed to load trips",
            isLoading: false,
          });
        }
      },

      removeDestination: async (tripId, destinationId) => {
        set({ error: null, isLoading: true });

        try {
          // This will be replaced with actual API call
          await new Promise((resolve) => setTimeout(resolve, 1000));

          set((state) => {
            const trips = state.trips.map((trip) => {
              if (trip.id === tripId) {
                return {
                  ...trip,
                  destinations: trip.destinations.filter(
                    (dest) => dest.id !== destinationId
                  ),
                  updatedAt: new Date().toISOString(),
                };
              }
              return trip;
            });

            const currentTrip =
              state.currentTrip?.id === tripId
                ? {
                    ...state.currentTrip,
                    destinations: state.currentTrip.destinations.filter(
                      (dest) => dest.id !== destinationId
                    ),
                    updatedAt: new Date().toISOString(),
                  }
                : state.currentTrip;

            return { currentTrip, isLoading: false, trips };
          });
        } catch (error) {
          set({
            error:
              error instanceof Error ? error.message : "Failed to remove destination",
            isLoading: false,
          });
        }
      },

      setCurrentTrip: (trip) => set({ currentTrip: trip }),

      setTrips: (trips) => set({ trips }),
      trips: [],

      updateDestination: async (tripId, destinationId, data) => {
        set({ error: null, isLoading: true });

        try {
          // This will be replaced with actual API call
          await new Promise((resolve) => setTimeout(resolve, 1000));

          set((state) => {
            const trips = state.trips.map((trip) => {
              if (trip.id === tripId) {
                return {
                  ...trip,
                  destinations: trip.destinations.map((dest) =>
                    dest.id === destinationId ? { ...dest, ...data } : dest
                  ),
                  updatedAt: new Date().toISOString(),
                };
              }
              return trip;
            });

            const currentTrip =
              state.currentTrip?.id === tripId
                ? {
                    ...state.currentTrip,
                    destinations: state.currentTrip.destinations.map((dest) =>
                      dest.id === destinationId ? { ...dest, ...data } : dest
                    ),
                    updatedAt: new Date().toISOString(),
                  }
                : state.currentTrip;

            return { currentTrip, isLoading: false, trips };
          });
        } catch (error) {
          set({
            error:
              error instanceof Error ? error.message : "Failed to update destination",
            isLoading: false,
          });
        }
      },

      updateTrip: async (id, data) => {
        set({ error: null, isLoading: true });

        try {
          const { updateTrip: repoUpdateTrip } = await import(
            "@/lib/repositories/trips-repo"
          );

          // Map to DB update shape
          const updateData: TripsUpdate = {};
          if (data.title) {
            updateData.name = data.title; // Database uses 'name', frontend uses 'title'
          }
          if (data.startDate) {
            updateData.start_date = data.startDate;
          }
          if (data.endDate) {
            updateData.end_date = data.endDate;
          }
          if (data.budget !== undefined) {
            updateData.budget = data.budget;
          }
          if (data.status) {
            updateData.status = data.status as TripsUpdate["status"];
          }
          if (data.preferences) {
            updateData.flexibility = data.preferences as Json;
          }
          if (data.tags) {
            updateData.notes = data.tags;
          }

          const existingTrip =
            _get().trips.find((trip) => trip.id === id) ?? _get().currentTrip;
          const ownerId = existingTrip?.userId ?? secureUuid();

          const updated = await repoUpdateTrip(
            Number.parseInt(id, 10),
            ownerId,
            updateData
          );
          const frontendTrip: Partial<Trip> = updated;

          set((state) => {
            const trips = state.trips.map((trip) =>
              trip.id === id ? { ...trip, ...frontendTrip } : trip
            );

            const currentTrip =
              state.currentTrip?.id === id
                ? { ...state.currentTrip, ...frontendTrip }
                : state.currentTrip;

            return { currentTrip, isLoading: false, trips };
          });
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : "Failed to update trip",
            isLoading: false,
          });
        }
      },
    }),
    {
      name: "trip-storage",
      partialize: (state) => ({
        currentTrip: state.currentTrip,
        trips: state.trips,
      }),
    }
  )
);
