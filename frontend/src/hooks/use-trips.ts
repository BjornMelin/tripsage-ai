"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { useAuthStore } from "@/stores";

export interface TripSuggestion {
  id: string;
  title: string;
  destination: string;
  description: string;
  image_url?: string | null;
  estimated_price: number;
  currency: string;
  duration: number;
  rating: number;
  category: "adventure" | "relaxation" | "culture" | "nature" | "city" | "beach";
  best_time_to_visit: string;
  highlights: string[];
  difficulty?: "easy" | "moderate" | "challenging";
  trending?: boolean;
  seasonal?: boolean;
  relevance_score?: number;
  metadata?: Record<string, any>;
}

interface TripSuggestionsParams {
  limit?: number;
  budget_max?: number;
  category?: string;
}

/**
 * Hook to fetch trip suggestions from the API
 */
export function useTripSuggestions(params?: TripSuggestionsParams) {
  const { tokenInfo } = useAuthStore();
  const isAuthenticated = !!tokenInfo?.access_token;

  return useQuery<TripSuggestion[]>({
    queryKey: ["trip-suggestions", params],
    queryFn: async () => {
      if (!isAuthenticated) {
        // Return empty array if not authenticated
        return [];
      }

      const response = await api.get<TripSuggestion[]>("/api/trips/suggestions", {
        params: {
          limit: params?.limit ?? 4,
          ...(params?.budget_max && { budget_max: params.budget_max }),
          ...(params?.category && { category: params.category }),
        },
      });

      return response;
    },
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  });
}

/**
 * Hook to create a new trip
 */
export function useCreateTrip() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (tripData: any) => {
      const response = await api.post("/api/trips", tripData);
      return response;
    },
    onSuccess: () => {
      // Invalidate trips list and suggestions
      queryClient.invalidateQueries({ queryKey: ["trips"] });
      queryClient.invalidateQueries({ queryKey: ["trip-suggestions"] });
    },
  });
}

/**
 * Hook to get user's trips
 */
export function useTrips() {
  const { tokenInfo } = useAuthStore();
  const isAuthenticated = !!tokenInfo?.access_token;

  return useQuery({
    queryKey: ["trips"],
    queryFn: async () => {
      if (!isAuthenticated) {
        return { items: [], total: 0 };
      }

      const response = await api.get("/api/trips");
      return response;
    },
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export interface UpcomingFlight {
  id: string;
  trip_id?: string;
  trip_name?: string;
  airline: string;
  airline_name: string;
  flight_number: string;
  origin: string;
  destination: string;
  departure_time: string;
  arrival_time: string;
  duration: number;
  stops: number;
  price: number;
  currency: string;
  cabin_class: string;
  seats_available?: number;
  status: "upcoming" | "boarding" | "delayed" | "cancelled";
  terminal?: string;
  gate?: string;
}

interface UpcomingFlightsParams {
  limit?: number;
}

/**
 * Hook to fetch upcoming flights from the API
 */
export function useUpcomingFlights(params?: UpcomingFlightsParams) {
  const { tokenInfo } = useAuthStore();
  const isAuthenticated = !!tokenInfo?.access_token;

  return useQuery<UpcomingFlight[]>({
    queryKey: ["upcoming-flights", params],
    queryFn: async () => {
      if (!isAuthenticated) {
        return [];
      }

      const response = await api.get<UpcomingFlight[]>("/api/flights/upcoming", {
        params: {
          limit: params?.limit ?? 10,
        },
      });

      return response;
    },
    enabled: isAuthenticated,
    staleTime: 2 * 60 * 1000, // 2 minutes (shorter for real-time data)
    gcTime: 5 * 60 * 1000, // 5 minutes
  });
}