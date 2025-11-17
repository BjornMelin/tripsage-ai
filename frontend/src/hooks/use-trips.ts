/**
 * @fileoverview Unified React hooks for trip-related API operations including CRUD
 * operations, suggestions, real-time updates, and flight data fetching with proper
 * error handling and caching.
 */

"use client";

import type { RealtimeChannel } from "@supabase/supabase-js";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useAuthenticatedApi } from "@/hooks/use-authenticated-api";
import { type AppError, handleApiError, isApiError } from "@/lib/api/error-types";
import { cacheTimes, queryKeys, staleTimes } from "@/lib/query-keys";
import { useSupabase } from "@/lib/supabase";
import type { UpdateTables } from "@/lib/supabase/database.types";
import type { Trip } from "@/stores/trip-store";

/** Represents a trip suggestion from the API. */
export interface TripSuggestion {
  /** Unique identifier for the trip suggestion. */
  readonly id: string;
  /** Title of the trip suggestion. */
  readonly title: string;
  /** Destination location. */
  readonly destination: string;
  /** Detailed description of the trip. */
  readonly description: string;
  /** URL to an image representing the trip destination. */
  readonly imageUrl?: string | null;
  /** Estimated cost of the trip. */
  readonly estimatedPrice: number;
  /** Currency code for the estimated price (e.g., "USD", "EUR"). */
  readonly currency: string;
  /** Duration of the trip in days. */
  readonly duration: number;
  /** Average rating out of 5 stars. */
  readonly rating: number;
  /** Category of the trip. */
  readonly category:
    | "adventure"
    | "relaxation"
    | "culture"
    | "nature"
    | "city"
    | "beach";
  /** Best time of year to visit this destination. */
  readonly bestTimeToVisit: string;
  /** Array of key highlights or attractions. */
  readonly highlights: readonly string[];
  /** Difficulty level of the trip. */
  readonly difficulty?: "easy" | "moderate" | "challenging";
  /** Whether this trip is currently trending. */
  readonly trending?: boolean;
  /** Whether this trip is seasonal. */
  readonly seasonal?: boolean;
  /** Relevance score for search ranking. */
  readonly relevanceScore?: number;
  /** Additional metadata as key-value pairs. */
  readonly metadata?: Record<string, unknown>;
}

/** Parameters for fetching trip suggestions. */
interface TripSuggestionsParams {
  /** Maximum number of suggestions to return. */
  readonly limit?: number;
  /** Maximum budget constraint. */
  readonly budgetMax?: number;
  /** Category filter for suggestions. */
  readonly category?: string;
}

/**
 * Hook to fetch trip suggestions from the API with enhanced caching.
 *
 * @param params Optional parameters for filtering and limiting suggestions.
 * @returns Query object containing trip suggestions data, loading state, and error state.
 */
export function useTripSuggestions(params?: TripSuggestionsParams) {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  const normalizedParams: Record<string, string | number | boolean> = {
    limit: params?.limit ?? 4,
  };

  if (params?.budgetMax) {
    normalizedParams.budget_max = params.budgetMax;
  }

  if (params?.category) {
    normalizedParams.category = params.category;
  }

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
      if (isApiError(error)) {
        if (error.status === 401 || error.status === 403) return false;
      }
      return failureCount < 2;
    },
    staleTime: staleTimes.suggestions,
    throwOnError: false,
  });
}

/** Data structure for creating a new trip. */
interface CreateTripData {
  /** Title of the trip. */
  readonly title: string;
  /** Destination location. */
  readonly destination: string;
  /** Detailed description. */
  readonly description: string;
  /** Start date of the trip. */
  readonly startDate: string;
  /** End date of the trip. */
  readonly endDate: string;
  /** Budget for the trip. */
  readonly budget?: number;
  /** Currency code for the budget. */
  readonly currency?: string;
  /** Additional metadata. */
  readonly metadata?: Record<string, unknown>;
}

/** Response from creating a new trip. */
interface TripResponse {
  /** Unique identifier of the created trip. */
  readonly id: string;
  /** Title of the trip. */
  readonly title: string;
  /** Destination location. */
  readonly destination: string;
  /** Creation timestamp. */
  readonly createdAt: string;
  /** Last update timestamp. */
  readonly updatedAt: string;
}

/**
 * Hook to create a new trip with optimistic updates.
 *
 * @returns Mutation object for creating trips with loading state and error handling.
 */
export function useCreateTrip() {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();
  const queryClient = useQueryClient();

  return useMutation<TripResponse, AppError, CreateTripData>({
    mutationFn: async (tripData: CreateTripData) => {
      try {
        return await makeAuthenticatedRequest<TripResponse>("/api/trips", {
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
      if (isApiError(error)) {
        if (error.status >= 400 && error.status < 500) return false; // Don't retry client errors
      }
      return failureCount < 1;
    },
    throwOnError: false,
  });
}

type TripTableUpdate = Omit<UpdateTables<"trips">, "id">;

/** Data structure for updating a trip. */
export type UpdateTripData = TripTableUpdate & {
  /** Optional camelCase or additional metadata fields supported by API */
  readonly title?: string;
  readonly description?: string;
  readonly startDate?: string;
  readonly endDate?: string;
  readonly currency?: string;
  readonly metadata?: Record<string, unknown>;
};

/**
 * Hook to update an existing trip.
 *
 * @returns Mutation object for updating trips with loading state and error handling.
 */
export function useUpdateTrip() {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();
  const queryClient = useQueryClient();

  return useMutation<
    TripResponse,
    AppError,
    { tripId: string | number; data: UpdateTripData }
  >({
    mutationFn: async ({ tripId, data }) => {
      try {
        const numericTripId =
          typeof tripId === "string" ? Number.parseInt(tripId, 10) : tripId;
        return await makeAuthenticatedRequest<TripResponse>(
          `/api/trips/${numericTripId}`,
          {
            body: JSON.stringify(data),
            headers: { "Content-Type": "application/json" },
            method: "PUT",
          }
        );
      } catch (error) {
        throw handleApiError(error);
      }
    },
    onSuccess: (_data, variables) => {
      const numericTripId =
        typeof variables.tripId === "string"
          ? Number.parseInt(variables.tripId, 10)
          : variables.tripId;
      // Invalidate specific trip and trips list
      queryClient.invalidateQueries({
        queryKey: queryKeys.trips.detail(numericTripId),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.trips.all() });
    },
    retry: (failureCount, error) => {
      if (isApiError(error)) {
        if (error.status >= 400 && error.status < 500) return false; // Don't retry client errors
      }
      return failureCount < 1;
    },
    throwOnError: false,
  });
}

/**
 * Hook to delete a trip.
 *
 * @returns Mutation object for deleting trips with loading state and error handling.
 */
export function useDeleteTrip() {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();
  const queryClient = useQueryClient();

  return useMutation<void, AppError, string | number>({
    mutationFn: async (tripId: string | number) => {
      try {
        const numericTripId =
          typeof tripId === "string" ? Number.parseInt(tripId, 10) : tripId;
        await makeAuthenticatedRequest(`/api/trips/${numericTripId}`, {
          method: "DELETE",
        });
      } catch (error) {
        throw handleApiError(error);
      }
    },
    onSuccess: (_data, tripId) => {
      const numericTripId =
        typeof tripId === "string" ? Number.parseInt(tripId, 10) : tripId;
      // Invalidate specific trip and trips list
      queryClient.invalidateQueries({
        queryKey: queryKeys.trips.detail(numericTripId),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.trips.all() });
    },
    retry: (failureCount, error) => {
      if (isApiError(error)) {
        if (error.status >= 400 && error.status < 500) return false; // Don't retry client errors
      }
      return failureCount < 1;
    },
    throwOnError: false,
  });
}

/** Parameters for filtering trips. */
interface TripFilters extends Record<string, unknown> {
  /** Filter by trip status. */
  readonly status?: string;
  /** Filter by destination. */
  readonly destination?: string;
  /** Filter by date range start. */
  readonly startDate?: string;
  /** Filter by date range end. */
  readonly endDate?: string;
  /** Maximum number of results. */
  readonly limit?: number;
  /** Offset for pagination. */
  readonly offset?: number;
}

/**
 * Converts filter values to API-compatible parameters.
 *
 * @param filters Optional filter object to convert.
 * @returns API parameters object or undefined if no filters provided.
 */
const convertToApiParams = (
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
 * Real-time connection status for trip subscriptions.
 */
interface TripRealtimeStatus {
  /** Whether the real-time connection is active. */
  isConnected: boolean;
  /** Array of connection errors encountered. */
  errors: Error[];
}

/**
 * Hook to get user's trips with enhanced error handling and real-time updates.
 *
 * @param filters Optional filters to apply to the trip query.
 * @returns Query object containing trips data, loading state, error state,
 * and real-time connection status.
 */
export function useTrips(filters?: TripFilters) {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();
  const supabase = useSupabase();
  const queryClient = useQueryClient();
  const channelRef = useRef<RealtimeChannel | null>(null);
  const [realtimeStatus, setRealtimeStatus] = useState<TripRealtimeStatus>({
    errors: [],
    isConnected: false,
  });

  const query = useQuery<Trip[], AppError>({
    gcTime: cacheTimes.medium,
    queryFn: async () => {
      try {
        return await makeAuthenticatedRequest<Trip[]>("/api/trips", {
          params: convertToApiParams(filters),
        });
      } catch (error) {
        throw handleApiError(error);
      }
    },
    queryKey: queryKeys.trips.list(filters),
    retry: (failureCount, error) => {
      if (isApiError(error)) {
        if (error.status === 401 || error.status === 403) return false;
      }
      return failureCount < 2;
    },
    staleTime: staleTimes.trips,
    throwOnError: false,
  });

  // Set up real-time subscription for trips
  useEffect(() => {
    let mounted = true;

    const setupRealtime = async () => {
      try {
        // Get current user ID
        const {
          data: { user },
        } = await supabase.auth.getUser();
        if (!user || !mounted) return;

        // Clean up existing channel
        if (channelRef.current) {
          await supabase.removeChannel(channelRef.current);
        }

        // Create new channel for trips table changes
        const channel = supabase
          .channel(`trips:${user.id}`)
          .on(
            "postgres_changes",
            {
              event: "*",
              filter: `user_id=eq.${user.id}`,
              schema: "public",
              table: "trips",
            },
            (payload) => {
              if (!mounted) return;

              // Invalidate queries to refetch updated data
              queryClient.invalidateQueries({
                queryKey: queryKeys.trips.all(),
              });

              // If we have a specific trip ID, invalidate that too
              if (
                payload.new &&
                typeof payload.new === "object" &&
                "id" in payload.new
              ) {
                const tripId = payload.new.id;
                if (typeof tripId === "string" || typeof tripId === "number") {
                  queryClient.invalidateQueries({
                    queryKey: queryKeys.trips.detail(
                      typeof tripId === "string" ? Number.parseInt(tripId, 10) : tripId
                    ),
                  });
                }
              }
            }
          )
          .subscribe((status) => {
            if (!mounted) return;

            setRealtimeStatus((prev) => ({
              ...prev,
              errors:
                status === "SUBSCRIBED"
                  ? []
                  : status === "CHANNEL_ERROR"
                    ? [...prev.errors, new Error("Real-time channel error")]
                    : prev.errors,
              isConnected: status === "SUBSCRIBED",
            }));
          });

        channelRef.current = channel;
      } catch (error) {
        if (!mounted) return;
        setRealtimeStatus((prev) => ({
          ...prev,
          errors: [
            ...prev.errors,
            error instanceof Error ? error : new Error(String(error)),
          ],
          isConnected: false,
        }));
      }
    };

    setupRealtime();

    return () => {
      mounted = false;
      if (channelRef.current) {
        supabase.removeChannel(channelRef.current).catch(() => {
          // Ignore cleanup errors
        });
        channelRef.current = null;
      }
    };
  }, [supabase, queryClient]);

  return {
    ...query,
    isConnected: realtimeStatus.isConnected,
    realtimeStatus,
  };
}

/**
 * Hook to fetch a single trip by ID with real-time updates.
 *
 * @param tripId The ID of the trip to fetch, or null/undefined to skip fetching.
 * @returns Query object containing trip data, loading state, error state,
 * and real-time connection status.
 */
export function useTrip(tripId: string | number | null | undefined) {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();
  const supabase = useSupabase();
  const queryClient = useQueryClient();
  const channelRef = useRef<RealtimeChannel | null>(null);
  const [realtimeStatus, setRealtimeStatus] = useState<TripRealtimeStatus>({
    errors: [],
    isConnected: false,
  });

  const numericTripId =
    tripId === null || tripId === undefined
      ? null
      : typeof tripId === "string"
        ? Number.parseInt(tripId, 10)
        : tripId;

  const query = useQuery<Trip | null, AppError>({
    enabled: numericTripId !== null,
    gcTime: cacheTimes.medium,
    queryFn: async () => {
      if (numericTripId === null) return null;
      try {
        return await makeAuthenticatedRequest<Trip>(`/api/trips/${numericTripId}`);
      } catch (error) {
        throw handleApiError(error);
      }
    },
    queryKey: queryKeys.trips.detail(numericTripId ?? 0),
    retry: (failureCount, error) => {
      if (isApiError(error)) {
        if (error.status === 401 || error.status === 403) return false;
      }
      return failureCount < 2;
    },
    staleTime: staleTimes.trips,
    throwOnError: false,
  });

  // Set up real-time subscription for specific trip
  useEffect(() => {
    if (numericTripId === null) {
      if (channelRef.current) {
        supabase.removeChannel(channelRef.current).catch(() => {
          // Ignore cleanup errors
        });
        channelRef.current = null;
      }
      setRealtimeStatus({ errors: [], isConnected: false });
      return;
    }

    let mounted = true;

    const setupRealtime = async () => {
      try {
        // Get current user ID
        const {
          data: { user },
        } = await supabase.auth.getUser();
        if (!user || !mounted) return;

        // Clean up existing channel
        if (channelRef.current) {
          await supabase.removeChannel(channelRef.current);
        }

        // Create new channel for this specific trip
        const channel = supabase
          .channel(`trip:${numericTripId}`)
          .on(
            "postgres_changes",
            {
              event: "*",
              filter: `id=eq.${numericTripId}`,
              schema: "public",
              table: "trips",
            },
            () => {
              if (!mounted) return;
              // Invalidate this trip's query to refetch updated data
              queryClient.invalidateQueries({
                queryKey: queryKeys.trips.detail(numericTripId),
              });
              // Also invalidate the list to keep it in sync
              queryClient.invalidateQueries({
                queryKey: queryKeys.trips.all(),
              });
            }
          )
          .subscribe((status) => {
            if (!mounted) return;

            setRealtimeStatus((prev) => ({
              ...prev,
              errors:
                status === "SUBSCRIBED"
                  ? []
                  : status === "CHANNEL_ERROR"
                    ? [...prev.errors, new Error("Real-time channel error")]
                    : prev.errors,
              isConnected: status === "SUBSCRIBED",
            }));
          });

        channelRef.current = channel;
      } catch (error) {
        if (!mounted) return;
        setRealtimeStatus((prev) => ({
          ...prev,
          errors: [
            ...prev.errors,
            error instanceof Error ? error : new Error(String(error)),
          ],
          isConnected: false,
        }));
      }
    };

    setupRealtime();

    return () => {
      mounted = false;
      if (channelRef.current) {
        supabase.removeChannel(channelRef.current).catch(() => {
          // Ignore cleanup errors
        });
        channelRef.current = null;
      }
    };
  }, [numericTripId, supabase, queryClient]);

  return {
    ...query,
    isConnected: realtimeStatus.isConnected,
    realtimeStatus,
  };
}

/** Represents an upcoming flight with detailed information. */
export interface UpcomingFlight {
  /** Unique identifier for the flight. */
  readonly id: string;
  /** Associated trip identifier if this flight is part of a trip. */
  readonly tripId?: string;
  /** Name of the associated trip. */
  readonly tripName?: string;
  /** Airline code (e.g., "AA", "DL"). */
  readonly airline: string;
  /** Full airline name. */
  readonly airlineName: string;
  /** Flight number (e.g., "AA123"). */
  readonly flightNumber: string;
  /** Departure airport code. */
  readonly origin: string;
  /** Arrival airport code. */
  readonly destination: string;
  /** Scheduled departure time in ISO format. */
  readonly departureTime: string;
  /** Scheduled arrival time in ISO format. */
  readonly arrivalTime: string;
  /** Flight duration in minutes. */
  readonly duration: number;
  /** Number of stops during the flight. */
  readonly stops: number;
  /** Ticket price. */
  readonly price: number;
  /** Currency code for the price. */
  readonly currency: string;
  /** Cabin class (e.g., "economy", "business", "first"). */
  readonly cabinClass: string;
  /** Number of seats still available. */
  readonly seatsAvailable?: number;
  /** Current flight status. */
  readonly status: "upcoming" | "boarding" | "delayed" | "cancelled";
  /** Departure terminal. */
  readonly terminal?: string;
  /** Departure gate. */
  readonly gate?: string;
}

/** Parameters for fetching upcoming flights. */
interface UpcomingFlightsParams {
  /** Maximum number of flights to return. */
  readonly limit?: number;
}

/**
 * Hook to fetch upcoming flights from the API with enhanced real-time handling.
 *
 * @param params Optional parameters for limiting flight results.
 * @returns Query object containing upcoming flights data with real-time updates.
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
      if (isApiError(error)) {
        if (error.status === 401 || error.status === 403) return false;
      }
      return failureCount < 3; // More retries for external flight API
    },
    staleTime: staleTimes.realtime, // 30 seconds for real-time flight data
    throwOnError: false,
  });
}
