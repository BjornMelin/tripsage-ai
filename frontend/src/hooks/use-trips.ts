"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuthenticatedApi } from "@/hooks/use-authenticated-api";
import { type AppError, handleApiError } from "@/lib/api/error-types";
import { cacheTimes, queryKeys, staleTimes } from "@/lib/query-keys";

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
  metadata?: Record<string, unknown>;
}

interface TripSuggestionsParams {
  limit?: number;
  budget_max?: number;
  category?: string;
}

/**
 * Hook to fetch trip suggestions from the API with enhanced caching
 */
export function useTripSuggestions(params?: TripSuggestionsParams) {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  const normalizedParams = {
    limit: params?.limit ?? 4,
    ...(params?.budget_max && { budget_max: params.budget_max }),
    ...(params?.category && { category: params.category }),
  };

  return useQuery<TripSuggestion[], AppError>({
    gcTime: cacheTimes.medium,
    queryFn: async () => {
      try {
        return await makeAuthenticatedRequest<TripSuggestion[]>(
          "/api/trips/suggestions",
          { params: normalizedParams }
        );
      } catch (error) {
        throw handleApiError(error);
      }
    },
    queryKey: queryKeys.trips.suggestions(normalizedParams),
    retry: (failureCount, error) => {
      if (error instanceof Error && "status" in error) {
        const status = (error as any).status;
        if (status === 401 || status === 403) return false;
      }
      return failureCount < 2;
    },
    staleTime: staleTimes.suggestions,
    throwOnError: false,
  });
}

/**
 * Hook to create a new trip with optimistic updates
 */
export function useCreateTrip() {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();
  const queryClient = useQueryClient();

  return useMutation<any, AppError, any>({
    mutationFn: async (tripData: any) => {
      try {
        return await makeAuthenticatedRequest("/api/trips", {
          body: JSON.stringify(tripData),
          headers: { "Content-Type": "application/json" },
          method: "POST",
        });
      } catch (error) {
        throw handleApiError(error);
      }
    },
    onSuccess: () => {
      // Invalidate and refetch trips lists
      queryClient.invalidateQueries({ queryKey: queryKeys.trips.all() });

      // Optionally invalidate suggestions if they might be affected
      queryClient.invalidateQueries({ queryKey: queryKeys.trips.suggestions() });
    },
    retry: (failureCount, error) => {
      if (error instanceof Error && "status" in error) {
        const status = (error as any).status;
        if (status >= 400 && status < 500) return false; // Don't retry client errors
      }
      return failureCount < 1;
    },
    throwOnError: false,
  });
}

// Helper function to convert unknown values to API params
const CONVERT_TO_API_PARAMS = (
  filters?: Record<string, unknown>
): Record<string, string | number | boolean> | undefined => {
  if (!filters) return undefined;

  const apiParams: Record<string, string | number | boolean> = {};

  for (const [key, value] of Object.entries(filters)) {
    if (value !== null && value !== undefined) {
      if (
        typeof value === "string" ||
        typeof value === "number" ||
        typeof value === "boolean"
      ) {
        apiParams[key] = value;
      } else {
        // Convert other types to string
        apiParams[key] = String(value);
      }
    }
  }

  return Object.keys(apiParams).length > 0 ? apiParams : undefined;
};

/**
 * Hook to get user's trips with enhanced error handling
 */
export function useTrips(filters?: Record<string, unknown>) {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  return useQuery<any[], AppError>({
    gcTime: cacheTimes.medium,
    queryFn: async () => {
      try {
        return await makeAuthenticatedRequest("/api/trips", {
          params: CONVERT_TO_API_PARAMS(filters),
        });
      } catch (error) {
        throw handleApiError(error);
      }
    },
    queryKey: queryKeys.trips.list(filters),
    retry: (failureCount, error) => {
      if (error instanceof Error && "status" in error) {
        const status = (error as any).status;
        if (status === 401 || status === 403) return false;
      }
      return failureCount < 2;
    },
    staleTime: staleTimes.trips,
    throwOnError: false,
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
 * Hook to fetch upcoming flights from the API with enhanced real-time handling
 */
export function useUpcomingFlights(params?: UpcomingFlightsParams) {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  const normalizedParams = {
    limit: params?.limit ?? 10,
  };

  return useQuery<UpcomingFlight[], AppError>({
    gcTime: cacheTimes.short, // 5 minutes
    queryFn: async () => {
      try {
        return await makeAuthenticatedRequest<UpcomingFlight[]>(
          "/api/flights/upcoming",
          { params: normalizedParams }
        );
      } catch (error) {
        throw handleApiError(error);
      }
    },
    queryKey: queryKeys.external.upcomingFlights(normalizedParams),
    refetchInterval: 2 * 60 * 1000, // Refetch every 2 minutes for fresh flight data
    refetchIntervalInBackground: false, // Only when page is visible
    retry: (failureCount, error) => {
      if (error instanceof Error && "status" in error) {
        const status = (error as any).status;
        if (status === 401 || status === 403) return false;
      }
      return failureCount < 3; // More retries for external flight API
    },
    staleTime: staleTimes.realtime, // 30 seconds for real-time flight data
    throwOnError: false,
  });
}
