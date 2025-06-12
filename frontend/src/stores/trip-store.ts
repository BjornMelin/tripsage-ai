import { create } from "zustand";
import { persist } from "zustand/middleware";
import { useSupabaseTrips } from "@/hooks/use-supabase-trips";
import { useQueryClient } from "@tanstack/react-query";

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

// Enhanced budget structure aligned with backend
export interface EnhancedBudget {
  total: number;
  currency: string;
  spent: number;
  breakdown: Record<string, number>;
}

// Enhanced preferences structure
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
  title: string; // Primary field name
  name?: string; // Legacy compatibility
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
  enhanced_budget?: EnhancedBudget; // New enhanced budget
  currency?: string;
  spent_amount?: number;

  // Enhanced fields
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
    (set, get) => ({
      trips: [],
      currentTrip: null,
      isLoading: false,
      error: null,

      setTrips: (trips) => set({ trips }),

      setCurrentTrip: (trip) => set({ currentTrip: trip }),

      loadTrips: async () => {
        set({ isLoading: true, error: null });

        try {
          const { supabase } = await import("@/lib/supabase/client");

          const { data: trips, error } = await supabase
            .from("trips")
            .select("*")
            .order("created_at", { ascending: false });

          if (error) throw error;

          // Convert to frontend format
          const frontendTrips: Trip[] = trips.map((trip) => ({
            id: trip.id.toString(),
            uuid_id: trip.uuid_id,
            user_id: trip.user_id,
            title: trip.title,
            name: trip.title, // Legacy compatibility
            description: trip.description,
            start_date: trip.start_date,
            startDate: trip.start_date, // Frontend compatibility
            end_date: trip.end_date,
            endDate: trip.end_date, // Frontend compatibility
            destinations: [], // Will be loaded separately or joined
            budget: trip.budget,
            enhanced_budget: trip.budget_breakdown
              ? {
                  total: trip.budget_breakdown.total || trip.budget || 0,
                  currency: trip.currency || "USD",
                  spent: trip.budget_breakdown.spent || trip.spent_amount || 0,
                  breakdown: trip.budget_breakdown.breakdown || {},
                }
              : undefined,
            currency: trip.currency,
            spent_amount: trip.spent_amount,
            visibility: trip.visibility,
            isPublic: trip.visibility !== "private", // Legacy compatibility
            tags: trip.tags || [],
            preferences: trip.preferences || {},
            status: trip.status,
            created_at: trip.created_at,
            createdAt: trip.created_at, // Frontend compatibility
            updated_at: trip.updated_at,
            updatedAt: trip.updated_at, // Frontend compatibility
          }));

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
          const { supabase } = await import("@/lib/supabase/client");

          const tripData = {
            title: data.title || data.name || "Untitled Trip",
            description: data.description || "",
            start_date: data.startDate || data.start_date,
            end_date: data.endDate || data.end_date,
            budget: data.budget,
            currency: data.currency || "USD",
            spent_amount: 0,
            visibility: data.visibility || "private",
            tags: data.tags || [],
            preferences: data.preferences || {},
            status: data.status || "planning",
            // Enhanced budget structure
            budget_breakdown: data.enhanced_budget
              ? {
                  total: data.enhanced_budget.total,
                  spent: data.enhanced_budget.spent,
                  breakdown: data.enhanced_budget.breakdown,
                }
              : data.budget
                ? {
                    total: data.budget,
                    spent: 0,
                    breakdown: {},
                  }
                : null,
          };

          const { data: newTrip, error } = await supabase
            .from("trips")
            .insert([tripData])
            .select()
            .single();

          if (error) throw error;

          // Convert to frontend format
          const frontendTrip: Trip = {
            id: newTrip.id.toString(),
            uuid_id: newTrip.uuid_id,
            user_id: newTrip.user_id,
            title: newTrip.title,
            name: newTrip.title, // Legacy compatibility
            description: newTrip.description,
            start_date: newTrip.start_date,
            startDate: newTrip.start_date, // Frontend compatibility
            end_date: newTrip.end_date,
            endDate: newTrip.end_date, // Frontend compatibility
            destinations: [], // Will be handled separately
            budget: newTrip.budget,
            enhanced_budget: newTrip.budget_breakdown
              ? {
                  total: newTrip.budget_breakdown.total || newTrip.budget || 0,
                  currency: newTrip.currency || "USD",
                  spent: newTrip.budget_breakdown.spent || newTrip.spent_amount || 0,
                  breakdown: newTrip.budget_breakdown.breakdown || {},
                }
              : undefined,
            currency: newTrip.currency,
            spent_amount: newTrip.spent_amount,
            visibility: newTrip.visibility,
            isPublic: newTrip.visibility !== "private", // Legacy compatibility
            tags: newTrip.tags || [],
            preferences: newTrip.preferences || {},
            status: newTrip.status,
            created_at: newTrip.created_at,
            createdAt: newTrip.created_at, // Frontend compatibility
            updated_at: newTrip.updated_at,
            updatedAt: newTrip.updated_at, // Frontend compatibility
          };

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
          const { supabase } = await import("@/lib/supabase/client");

          const updateData: any = {};

          // Map frontend fields to database fields
          if (data.title || data.name) updateData.title = data.title || data.name;
          if (data.description !== undefined) updateData.description = data.description;
          if (data.startDate || data.start_date)
            updateData.start_date = data.startDate || data.start_date;
          if (data.endDate || data.end_date)
            updateData.end_date = data.endDate || data.end_date;
          if (data.budget !== undefined) updateData.budget = data.budget;
          if (data.currency) updateData.currency = data.currency;
          if (data.spent_amount !== undefined)
            updateData.spent_amount = data.spent_amount;
          if (data.visibility) updateData.visibility = data.visibility;
          if (data.tags) updateData.tags = data.tags;
          if (data.preferences) updateData.preferences = data.preferences;
          if (data.status) updateData.status = data.status;

          // Handle enhanced budget
          if (data.enhanced_budget) {
            updateData.budget_breakdown = {
              total: data.enhanced_budget.total,
              spent: data.enhanced_budget.spent,
              breakdown: data.enhanced_budget.breakdown,
            };
            updateData.budget = data.enhanced_budget.total;
            updateData.spent_amount = data.enhanced_budget.spent;
            updateData.currency = data.enhanced_budget.currency;
          }

          const { data: updatedTrip, error } = await supabase
            .from("trips")
            .update(updateData)
            .eq("id", Number.parseInt(id))
            .select()
            .single();

          if (error) throw error;

          // Convert to frontend format
          const frontendTrip: Partial<Trip> = {
            id: updatedTrip.id.toString(),
            uuid_id: updatedTrip.uuid_id,
            title: updatedTrip.title,
            name: updatedTrip.title, // Legacy compatibility
            description: updatedTrip.description,
            start_date: updatedTrip.start_date,
            startDate: updatedTrip.start_date, // Frontend compatibility
            end_date: updatedTrip.end_date,
            endDate: updatedTrip.end_date, // Frontend compatibility
            budget: updatedTrip.budget,
            enhanced_budget: updatedTrip.budget_breakdown
              ? {
                  total: updatedTrip.budget_breakdown.total || updatedTrip.budget || 0,
                  currency: updatedTrip.currency || "USD",
                  spent:
                    updatedTrip.budget_breakdown.spent || updatedTrip.spent_amount || 0,
                  breakdown: updatedTrip.budget_breakdown.breakdown || {},
                }
              : undefined,
            currency: updatedTrip.currency,
            spent_amount: updatedTrip.spent_amount,
            visibility: updatedTrip.visibility,
            isPublic: updatedTrip.visibility !== "private", // Legacy compatibility
            tags: updatedTrip.tags || [],
            preferences: updatedTrip.preferences || {},
            status: updatedTrip.status,
            updated_at: updatedTrip.updated_at,
            updatedAt: updatedTrip.updated_at, // Frontend compatibility
          };

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
          const { supabase } = await import("@/lib/supabase/client");

          const { error } = await supabase
            .from("trips")
            .delete()
            .eq("id", Number.parseInt(id));

          if (error) throw error;

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
