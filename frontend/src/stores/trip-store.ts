import { create } from "zustand";
import { persist } from "zustand/middleware";

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

export interface Trip {
  id: string;
  name: string;
  description?: string;
  startDate?: string;
  endDate?: string;
  destinations: Destination[];
  budget?: number;
  currency?: string;
  isPublic: boolean;
  createdAt: string;
  updatedAt: string;
}

interface TripState {
  trips: Trip[];
  currentTrip: Trip | null;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  setTrips: (trips: Trip[]) => void;
  setCurrentTrip: (trip: Trip | null) => void;
  createTrip: (data: Partial<Trip>) => Promise<void>;
  updateTrip: (id: string, data: Partial<Trip>) => Promise<void>;
  deleteTrip: (id: string) => Promise<void>;
  addDestination: (tripId: string, destination: Destination) => Promise<void>;
  updateDestination: (tripId: string, destinationId: string, data: Partial<Destination>) => Promise<void>;
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
      
      createTrip: async (data) => {
        set({ isLoading: true, error: null });
        
        try {
          // This will be replaced with actual API call
          await new Promise((resolve) => setTimeout(resolve, 1000));
          
          const newTrip: Trip = {
            id: Date.now().toString(),
            name: data.name || "Untitled Trip",
            description: data.description || "",
            startDate: data.startDate,
            endDate: data.endDate,
            destinations: data.destinations || [],
            budget: data.budget,
            currency: data.currency || "USD",
            isPublic: data.isPublic || false,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          };
          
          set((state) => ({
            trips: [...state.trips, newTrip],
            currentTrip: newTrip,
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
          // This will be replaced with actual API call
          await new Promise((resolve) => setTimeout(resolve, 1000));
          
          set((state) => {
            const trips = state.trips.map((trip) => 
              trip.id === id
                ? {
                    ...trip,
                    ...data,
                    updatedAt: new Date().toISOString(),
                  }
                : trip
            );
            
            const currentTrip = state.currentTrip?.id === id
              ? { ...state.currentTrip, ...data, updatedAt: new Date().toISOString() }
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
          // This will be replaced with actual API call
          await new Promise((resolve) => setTimeout(resolve, 1000));
          
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
            
            const currentTrip = state.currentTrip?.id === tripId
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
            
            const currentTrip = state.currentTrip?.id === tripId
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
            error: error instanceof Error ? error.message : "Failed to update destination",
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
                  destinations: trip.destinations.filter((dest) => dest.id !== destinationId),
                  updatedAt: new Date().toISOString(),
                };
              }
              return trip;
            });
            
            const currentTrip = state.currentTrip?.id === tripId
              ? {
                  ...state.currentTrip,
                  destinations: state.currentTrip.destinations.filter((dest) => dest.id !== destinationId),
                  updatedAt: new Date().toISOString(),
                }
              : state.currentTrip;
            
            return { trips, currentTrip, isLoading: false };
          });
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : "Failed to remove destination",
            isLoading: false,
          });
        }
      },
      
      clearError: () => set({ error: null }),
    }),
    {
      name: "trip-storage",
      partialize: (state) => ({ trips: state.trips, currentTrip: state.currentTrip }),
    }
  )
);