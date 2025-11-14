/**
 * @fileoverview Trip store using Zustand for managing trip state, including CRUD operations,
 * destination management, budget tracking, and persistence with local storage.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Json, UpdateTables } from "@/lib/supabase/database.types";

/**
 * Interface representing a destination within a trip.
 */
export interface Destination {
  id: string;
  name: string;
  country: string;
  coordinates?: {
    latitude: number;
    longitude: number;
  };
  startDate?: string;
  endDate?: string;
  activities?: string[];
  accommodation?: {
    type: string;
    name: string;
    price?: number;
  };
  transportation?: {
    type: string;
    details: string;
    price?: number;
  };
  estimatedCost?: number;
  notes?: string;
}

/**
 * Interface representing a trip budget with spending breakdown.
 */
export interface Budget {
  total: number;
  currency: string;
  spent: number;
  breakdown: Record<string, number>;
}

/**
 * Interface representing trip preferences including budget, accommodation, transportation, etc.
 */
export interface TripPreferences {
  budget?: {
    total?: number;
    currency?: string;
    accommodationBudget?: number;
    transportationBudget?: number;
    foodBudget?: number;
    activitiesBudget?: number;
  };
  accommodation?: {
    type?: string;
    minRating?: number;
    amenities?: string[];
    locationPreference?: string;
  };
  transportation?: {
    flightPreferences?: {
      seatClass?: string;
      maxStops?: number;
      preferredAirlines?: string[];
      timeWindow?: string;
    };
    localTransportation?: string[];
  };
  activities?: string[];
  dietaryRestrictions?: string[];
  accessibilityNeeds?: string[];
  [key: string]: unknown; // Allow additional preferences
}

/**
 * Interface representing a complete trip with all associated data.
 */
export interface Trip {
  // ID fields - supporting both database and UI representations
  id: string;
  // biome-ignore lint/style/useNamingConvention: Database uses snake_case
  uuid_id?: string;
  // biome-ignore lint/style/useNamingConvention: Database uses snake_case
  user_id?: string;

  // Core trip information (aligned with backend)
  name: string; // Primary field name from database
  title?: string; // Optional secondary name
  description?: string;

  // Date fields - supporting both formats
  // biome-ignore lint/style/useNamingConvention: Database uses snake_case
  start_date?: string; // Snake case for API compatibility
  // biome-ignore lint/style/useNamingConvention: Database uses snake_case
  end_date?: string; // Snake case for API compatibility
  startDate?: string; // Camel case for frontend compatibility
  endDate?: string; // Camel case for frontend compatibility

  // Trip details
  destinations: Destination[];

  // Budget - supporting both simple and structured representations
  budget?: number; // Simple total budget
  // biome-ignore lint/style/useNamingConvention: Database uses snake_case
  budget_breakdown?: Budget; // New enhanced budget
  currency?: string;
  // biome-ignore lint/style/useNamingConvention: Database uses snake_case
  spent_amount?: number;

  // fields
  visibility?: "private" | "shared" | "public";
  isPublic?: boolean; // Boolean mirror of visibility for older payloads
  tags?: string[];
  preferences?: TripPreferences;
  status?: string;

  // Timestamp fields - supporting both formats
  // biome-ignore lint/style/useNamingConvention: Database uses snake_case
  created_at?: string; // Snake case for API compatibility
  // biome-ignore lint/style/useNamingConvention: Database uses snake_case
  updated_at?: string; // Snake case for API compatibility
  createdAt?: string; // Camel case for frontend compatibility
  updatedAt?: string; // Camel case for frontend compatibility
}

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
            id: destination.id || Date.now().toString(),
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

          const tripData = {
            budget: data.budget,
            budgetBreakdown: data.budget_breakdown
              ? {
                  breakdown: data.budget_breakdown.breakdown,
                  spent: data.budget_breakdown.spent,
                  total: data.budget_breakdown.total,
                }
              : data.budget
                ? {
                    breakdown: {},
                    spent: 0,
                    total: data.budget,
                  }
                : null,
            currency: data.currency ?? "USD",
            description: data.description ?? "",
            endDate: data.endDate ?? data.end_date,
            preferences: data.preferences ?? {},
            spentAmount: 0,
            startDate: data.startDate ?? data.start_date,
            status: data.status ?? "planning",
            tags: data.tags ?? [],
            title: data.title ?? data.name ?? "Untitled Trip",
            visibility: data.visibility ?? (data.isPublic ? "public" : "private"),
          };

          const created = await repoCreateTrip({
            budget: tripData.budget ?? 0,
            destination: (data as { destination?: string })?.destination ?? "",
            // biome-ignore lint/style/useNamingConvention: Database API requires snake_case
            end_date: tripData.endDate ?? new Date().toISOString(),
            flexibility: (tripData.preferences ?? {}) as Json,
            name: tripData.title,
            notes: tripData.tags ?? [],
            // biome-ignore lint/style/useNamingConvention: Database API requires snake_case
            search_metadata: {},
            // biome-ignore lint/style/useNamingConvention: Database API requires snake_case
            start_date: tripData.startDate ?? new Date().toISOString(),
            travelers: 1,
            // biome-ignore lint/style/useNamingConvention: Database API requires snake_case
            user_id: (data.user_id as string | undefined) ?? "",
          });

          // Convert to frontend format
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
          await repoDeleteTrip(
            Number.parseInt(id, 10),
            _get().currentTrip?.user_id || undefined
          );

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
          const updateData: UpdateTables<"trips"> = {};
          if (data.name ?? data.title) {
            updateData.name = data.name ?? data.title ?? "";
          }
          if (data.startDate ?? data.start_date) {
            updateData.start_date = data.startDate ?? data.start_date ?? "";
          }
          if (data.endDate ?? data.end_date) {
            updateData.end_date = data.endDate ?? data.end_date ?? "";
          }
          if (typeof data.budget === "number") {
            updateData.budget = data.budget;
          }
          if (data.status) {
            updateData.status = data.status as UpdateTables<"trips">["status"];
          }
          if (data.preferences) {
            updateData.flexibility = data.preferences as Json;
          }
          if (data.tags) {
            updateData.notes = data.tags;
          }

          const updated = await repoUpdateTrip(
            Number.parseInt(id, 10),
            _get().currentTrip?.user_id ?? "",
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
