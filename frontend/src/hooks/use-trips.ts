"use client";

import { useAuthenticatedApi } from "@/hooks/use-authenticated-api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

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
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  return useQuery<TripSuggestion[]>({
    queryKey: ["trip-suggestions", params],
    queryFn: async () => {
      const response = await makeAuthenticatedRequest<TripSuggestion[]>(
        "/api/trips/suggestions",
        {
          params: {
            limit: params?.limit ?? 4,
            ...(params?.budget_max && { budget_max: params.budget_max }),
            ...(params?.category && { category: params.category }),
          },
        }
      );

      return response;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  });
}

/**
 * Hook to create a new trip
 */
export function useCreateTrip() {
  const queryClient = useQueryClient();
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  const mutation = useMutation({
    mutationFn: async (tripData: any) => {
      const response = await makeAuthenticatedRequest("/api/trips", {
        method: "POST",
        body: JSON.stringify(tripData),
        headers: { "Content-Type": "application/json" },
      });
      return response;
    },
  });

  useEffect(() => {
    if (mutation.data) {
      // Invalidate trips list and suggestions
      queryClient.invalidateQueries({ queryKey: ["trips"] });
      queryClient.invalidateQueries({ queryKey: ["trip-suggestions"] });
    }
  }, [mutation.data, queryClient]);

  return mutation;
}

/**
 * Hook to get user's trips
 */
export function useTrips() {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  return useQuery({
    queryKey: ["trips"],
    queryFn: async () => {
      const response = await makeAuthenticatedRequest("/api/trips");
      return response;
    },
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
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  return useQuery<UpcomingFlight[]>({
    queryKey: ["upcoming-flights", params],
    queryFn: async () => {
      const response = await makeAuthenticatedRequest<UpcomingFlight[]>(
        "/api/flights/upcoming",
        {
          params: {
            limit: params?.limit ?? 10,
          },
        }
      );

      return response;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes (shorter for real-time data)
    gcTime: 5 * 60 * 1000, // 5 minutes
  });
}
