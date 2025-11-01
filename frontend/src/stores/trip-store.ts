import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Trip as DatabaseTrip } from "@/lib/supabase/database.types";

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

// budget structure aligned with backend
export interface Budget {
  total: number;
  currency: string;
  spent: number;
  breakdown: Record<string, number>;
}

// preferences structure
export interface TripPreferences {
  budget?: {
    total?: number;
    currency?: string;
    accommodation_budget?: number;
    transportation_budget?: number;
    food_budget?: number;
    activities_budget?: number;
  };
  accommodation?: {
    type?: string;
    min_rating?: number;
    amenities?: string[];
    location_preference?: string;
  };
  transportation?: {
    flight_preferences?: {
      seat_class?: string;
      max_stops?: number;
      preferred_airlines?: string[];
      time_window?: string;
    };
    local_transportation?: string[];
  };
  activities?: string[];
  dietary_restrictions?: string[];
  accessibility_needs?: string[];
  [key: string]: any; // Allow additional preferences
}

export interface Trip {
  // ID fields - supporting both legacy and new systems
  id: string;
  uuid_id?: string;
  user_id?: string;

  // Core trip information (aligned with backend)
  name: string; // Primary field name from database
  title?: string; // Optional secondary name
  description?: string;

  // Date fields - supporting both formats
  start_date?: string; // Snake case for API compatibility
  end_date?: string; // Snake case for API compatibility
  startDate?: string; // Camel case for frontend compatibility
  endDate?: string; // Camel case for frontend compatibility

  // Trip details
  destinations: Destination[];

  // Budget - supporting both legacy and enhanced
  budget?: number; // Legacy simple budget
  budget_breakdown?: Budget; // New enhanced budget
  currency?: string;
  spent_amount?: number;

  // fields
  visibility?: "private" | "shared" | "public";
  isPublic?: boolean; // Legacy field for backward compatibility
  tags?: string[];
  preferences?: TripPreferences;
  status?: string;

  // Timestamp fields - supporting both formats
  created_at?: string; // Snake case for API compatibility
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

export const useTripStore = create<TripState>()(
  persist(
    (set, _get) => ({
      trips: [],
      currentTrip: null,
      isLoading: false,
      error: null,

      setTrips: (trips) => set({ trips }),

      setCurrentTrip: (trip) => set({ currentTrip: trip }),

      loadTrips: async () => {
        set({ isLoading: true, error: null });

        try {
          const { listTrips } = await import("@/lib/repositories/trips-repo");
          const frontendTrips = await listTrips();
          set({ trips: frontendTrips, isLoading: false });
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : "Failed to load trips",
            isLoading: false,
          });
        }
      },

      createTrip: async (data) => {
        set({ isLoading: true, error: null });

        try {
          // Import hook will need to be used in component that calls this
          // For now, we'll use the supabase client directly
          const { createTrip: repoCreateTrip } = await import(
            "@/lib/repositories/trips-repo"
          );

          const tripData = {
            title: data.title || data.name || "Untitled Trip",
            description: data.description || "",
            start_date: data.startDate || data.start_date,
            end_date: data.endDate || data.end_date,
            budget: data.budget,
            currency: data.currency || "USD",
            spent_amount: 0,
            visibility: data.visibility || (data.isPublic ? "public" : "private"),
            tags: data.tags || [],
            preferences: data.preferences || {},
            status: data.status || "planning",
            // budget structure
            budget_breakdown: data.budget_breakdown
              ? {
                  total: data.budget_breakdown.total,
                  spent: data.budget_breakdown.spent,
                  breakdown: data.budget_breakdown.breakdown,
                }
              : data.budget
                ? {
                    total: data.budget,
                    spent: 0,
                    breakdown: {},
                  }
                : null,
          };

          const created = await repoCreateTrip({
            user_id: (data.user_id as string) || "",
            name: tripData.title,
            start_date: tripData.start_date || new Date().toISOString(),
            end_date: tripData.end_date || new Date().toISOString(),
            destination: (data as { destination?: string })?.destination || "",
            budget: tripData.budget || 0,
            travelers: 1,
            search_metadata: {},
            flexibility: {},
          });

          // Convert to frontend format
          const frontendTrip: Trip = created as any;

          set((state) => ({
            trips: [...state.trips, frontendTrip],
            currentTrip: frontendTrip,
            isLoading: false,
          }));
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : "Failed to create trip",
            isLoading: false,
          });
        }
      },

      updateTrip: async (id, data) => {
        set({ isLoading: true, error: null });

        try {
          const { updateTrip: repoUpdateTrip } = await import(
            "@/lib/repositories/trips-repo"
          );

          // Map to DB update shape
          const updateData: Partial<DatabaseTrip> = {} as Partial<DatabaseTrip>;
          if (data.name || data.title) updateData.name = data.name || data.title!;
          if (data.startDate || data.start_date)
            updateData.start_date = (data.startDate || data.start_date)!;
          if (data.endDate || data.end_date)
            updateData.end_date = (data.endDate || data.end_date)!;
          if (typeof data.budget === "number") updateData.budget = data.budget;
          if (data.status) updateData.status = data.status as DatabaseTrip["status"];
          if (data.preferences) updateData.flexibility = data.preferences as any;
          if (data.tags) updateData.notes = data.tags as string[];

          const updated = await repoUpdateTrip(
            Number.parseInt(id, 10),
            _get().currentTrip?.user_id || "",
            updateData as any
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

            return { trips, currentTrip, isLoading: false };
          });
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : "Failed to update trip",
            isLoading: false,
          });
        }
      },

      deleteTrip: async (id) => {
        set({ isLoading: true, error: null });

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

            return { trips, currentTrip, isLoading: false };
          });
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : "Failed to delete trip",
            isLoading: false,
          });
        }
      },

      addDestination: async (tripId, destination) => {
        set({ isLoading: true, error: null });

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

            return { trips, currentTrip, isLoading: false };
          });
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : "Failed to add destination",
            isLoading: false,
          });
        }
      },

      updateDestination: async (tripId, destinationId, data) => {
        set({ isLoading: true, error: null });

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

            return { trips, currentTrip, isLoading: false };
          });
        } catch (error) {
          set({
            error:
              error instanceof Error ? error.message : "Failed to update destination",
            isLoading: false,
          });
        }
      },

      removeDestination: async (tripId, destinationId) => {
        set({ isLoading: true, error: null });

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

            return { trips, currentTrip, isLoading: false };
          });
        } catch (error) {
          set({
            error:
              error instanceof Error ? error.message : "Failed to remove destination",
            isLoading: false,
          });
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: "trip-storage",
      partialize: (state) => ({
        trips: state.trips,
        currentTrip: state.currentTrip,
      }),
    }
  )
);
