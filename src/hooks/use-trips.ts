/**
 * @fileoverview Unified React hooks for trip-related API operations including CRUD operations, suggestions, real-time updates, and flight data fetching with proper error handling and caching.
 */

"use client";

import type {
  TripCreateInput,
  TripFilters,
  TripSuggestion,
  TripUpdateInput,
  UiTrip,
} from "@schemas/trips";
import type { RealtimePostgresChangesPayload } from "@supabase/supabase-js";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useMemo } from "react";
import {
  type PostgresChangesSubscription,
  usePostgresChangesChannel,
} from "@/hooks/supabase/use-realtime-channel";
import { useAuthenticatedApi } from "@/hooks/use-authenticated-api";
import { useCurrentUserId } from "@/hooks/use-current-user-id";
import { type AppError, handleApiError } from "@/lib/api/error-types";
import { keys } from "@/lib/keys";
import { cacheTimes, staleTimes } from "@/lib/query/config";
import type { TablesUpdate } from "@/lib/supabase/database.types";

/** Trip type alias using canonical schema from @schemas/trips. */
export type Trip = UiTrip;

/** Re-export TripSuggestion type for convenience. */
export type { TripSuggestion };

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
  const userId = useCurrentUserId();

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
    enabled: !!userId,
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
    queryKey: userId
      ? keys.trips.suggestion(userId, normalizedParams)
      : keys.trips.listDisabled(),
    staleTime: staleTimes.suggestions,
    throwOnError: false,
  });
}

/**
 * Hook to create a new trip with optimistic updates.
 *
 * @returns Mutation object for creating trips with loading state and error handling.
 */
export function useCreateTrip() {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();
  const queryClient = useQueryClient();
  const userId = useCurrentUserId();

  return useMutation<UiTrip, AppError, TripCreateInput>({
    mutationFn: async (tripData: TripCreateInput) => {
      try {
        return await makeAuthenticatedRequest<UiTrip>("/api/trips", {
          body: JSON.stringify(tripData),
          headers: { "Content-Type": "application/json" },
          method: "POST",
        });
      } catch (error) {
        throw handleApiError(error);
      }
    },
    onSuccess: () => {
      if (userId) {
        queryClient.invalidateQueries({ queryKey: keys.trips.user(userId) });
        queryClient.invalidateQueries({ queryKey: keys.trips.suggestions(userId) });
        return;
      }

      queryClient.invalidateQueries({ queryKey: keys.trips.all() });
    },
    throwOnError: false,
  });
}

type TripTableUpdate = Omit<TablesUpdate<"trips">, "id">;

/** Data structure for updating a trip. */
export type UpdateTripData = TripUpdateInput & TripTableUpdate;

/**
 * Hook to update an existing trip.
 *
 * @returns Mutation object for updating trips with loading state and error handling.
 */
export function useUpdateTrip() {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();
  const queryClient = useQueryClient();
  const userId = useCurrentUserId();

  return useMutation<
    UiTrip,
    AppError,
    { tripId: string | number; data: UpdateTripData }
  >({
    mutationFn: async ({ tripId, data }) => {
      try {
        const numericTripId =
          typeof tripId === "string" ? Number.parseInt(tripId, 10) : tripId;
        return await makeAuthenticatedRequest<UiTrip>(`/api/trips/${numericTripId}`, {
          body: JSON.stringify(data),
          headers: { "Content-Type": "application/json" },
          method: "PUT",
        });
      } catch (error) {
        throw handleApiError(error);
      }
    },
    onSuccess: (_data, variables) => {
      const numericTripId =
        typeof variables.tripId === "string"
          ? Number.parseInt(variables.tripId, 10)
          : variables.tripId;

      if (userId) {
        queryClient.invalidateQueries({
          queryKey: keys.trips.detail(userId, numericTripId),
        });
        queryClient.invalidateQueries({ queryKey: keys.trips.lists(userId) });
        return;
      }

      queryClient.invalidateQueries({ queryKey: keys.trips.all() });
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
  const userId = useCurrentUserId();

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

      if (userId) {
        queryClient.invalidateQueries({
          queryKey: keys.trips.detail(userId, numericTripId),
        });
        queryClient.invalidateQueries({ queryKey: keys.trips.lists(userId) });
        return;
      }

      queryClient.invalidateQueries({ queryKey: keys.trips.all() });
    },
    throwOnError: false,
  });
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
export function useTrips(filters?: TripFilters, options?: { userId?: string | null }) {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();
  const queryClient = useQueryClient();
  const inferredUserId = useCurrentUserId();
  const userId = options?.userId ?? inferredUserId;
  const apiParams = convertToApiParams(filters);

  const query = useQuery<Trip[], AppError>({
    enabled: !!userId,
    gcTime: cacheTimes.medium,
    queryFn: async () => {
      try {
        return await makeAuthenticatedRequest<Trip[]>("/api/trips", {
          params: apiParams,
        });
      } catch (error) {
        throw handleApiError(error);
      }
    },
    queryKey: userId ? keys.trips.list(userId, apiParams) : keys.trips.listDisabled(),
    staleTime: staleTimes.trips,
    throwOnError: false,
  });

  const realtimeTopic = userId ? `trips:${userId}` : null;
  const changes = useMemo<PostgresChangesSubscription[]>(
    () =>
      userId
        ? [
            {
              event: "*",
              schema: "public",
              table: "trips",
            },
            {
              event: "*",
              filter: `user_id=eq.${userId}`,
              schema: "public",
              table: "trip_collaborators",
            },
          ]
        : [],
    [userId]
  );

  type TripsRealtimeRow = { id?: number | string } & Partial<
    Record<"trip_id", number | string>
  >;

  const getRealtimeNumberishField = useCallback(
    (row: unknown, field: "id" | "trip_id") => {
      if (!row || typeof row !== "object") return undefined;
      const value = (row as Record<string, unknown>)[field];
      return typeof value === "string" || typeof value === "number" ? value : undefined;
    },
    []
  );

  const handleTripsChange = useCallback(
    (payload: RealtimePostgresChangesPayload<TripsRealtimeRow>) => {
      if (userId) {
        queryClient.invalidateQueries({ queryKey: keys.trips.user(userId) });
      } else {
        queryClient.invalidateQueries({ queryKey: keys.trips.all() });
      }

      const rawTripId =
        payload.table === "trip_collaborators"
          ? (getRealtimeNumberishField(payload.new, "trip_id") ??
            getRealtimeNumberishField(payload.old, "trip_id"))
          : (getRealtimeNumberishField(payload.new, "id") ??
            getRealtimeNumberishField(payload.old, "id"));

      if (!rawTripId) return;

      const numericId =
        typeof rawTripId === "string" ? Number.parseInt(rawTripId, 10) : rawTripId;

      if (Number.isFinite(numericId)) {
        if (userId) {
          queryClient.invalidateQueries({
            queryKey: keys.trips.detail(userId, numericId),
          });
        }
      }
    },
    [getRealtimeNumberishField, queryClient, userId]
  );

  const realtime = usePostgresChangesChannel<TripsRealtimeRow>(realtimeTopic, {
    changes,
    onChange: handleTripsChange,
    private: true,
  });

  const realtimeStatus = useMemo<TripRealtimeStatus>(
    () => ({
      errors: realtime.error ? [realtime.error] : [],
      isConnected: realtime.connectionStatus === "subscribed",
    }),
    [realtime.connectionStatus, realtime.error]
  );

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
export function useTrip(
  tripId: string | number | null | undefined,
  options?: { userId?: string | null }
) {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();
  const queryClient = useQueryClient();
  const inferredUserId = useCurrentUserId();
  const userId = options?.userId ?? inferredUserId;

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
    queryKey:
      numericTripId !== null
        ? keys.trips.detail(userId ?? "no-user", numericTripId)
        : keys.trips.detailDisabled(),
    staleTime: staleTimes.trips,
    throwOnError: false,
  });

  const realtimeTopic =
    userId && numericTripId !== null ? `trip:${numericTripId}` : null;
  const changes = useMemo<PostgresChangesSubscription[]>(
    () =>
      numericTripId !== null && userId
        ? [
            {
              event: "*",
              filter: `id=eq.${numericTripId}`,
              schema: "public",
              table: "trips",
            },
          ]
        : [],
    [numericTripId, userId]
  );

  const handleTripChange = useCallback(() => {
    if (numericTripId === null) return;
    if (!userId) return;
    queryClient.invalidateQueries({
      queryKey: keys.trips.detail(userId, numericTripId),
    });
    queryClient.invalidateQueries({ queryKey: keys.trips.lists(userId) });
  }, [numericTripId, queryClient, userId]);

  const realtime = usePostgresChangesChannel(realtimeTopic, {
    changes,
    onChange: handleTripChange,
    private: true,
  });

  const realtimeStatus = useMemo<TripRealtimeStatus>(
    () => ({
      errors: realtime.error ? [realtime.error] : [],
      isConnected: realtime.connectionStatus === "subscribed",
    }),
    [realtime.connectionStatus, realtime.error]
  );

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
    queryKey: keys.external.upcomingFlights(normalizedParams),
    refetchInterval: 2 * 60 * 1000, // Refetch every 2 minutes for fresh flight data
    refetchIntervalInBackground: false, // Only when page is visible
    staleTime: staleTimes.realtime, // 30 seconds for real-time flight data
    throwOnError: false,
  });
}
