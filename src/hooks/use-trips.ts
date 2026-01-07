/**
 * @fileoverview Unified React Query hooks for trip operations (CRUD, suggestions, itinerary).
 */

"use client";

import type {
  ItineraryItem,
  ItineraryItemUpsertInput,
  TripCreateInput,
  TripFilters,
  TripSuggestion,
  TripUpdateInput,
  UiTrip,
} from "@schemas/trips";
import type { QueryKey } from "@tanstack/react-query";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuthenticatedApi } from "@/hooks/use-authenticated-api";
import { useCurrentUserId } from "@/hooks/use-current-user-id";
import { ApiError, type ApiErrorCode, type AppError } from "@/lib/api/error-types";
import { keys } from "@/lib/keys";
import { cacheTimes, staleTimes } from "@/lib/query/config";
import type { Result, ResultError } from "@/lib/result";
import { nowIso, secureId } from "@/lib/security/random";
import {
  createTrip as createTripAction,
  deleteItineraryItem as deleteItineraryItemAction,
  deleteTrip as deleteTripAction,
  getTripById as getTripByIdAction,
  getTripItinerary as getTripItineraryAction,
  getTripsForUser as getTripsForUserAction,
  updateTrip as updateTripAction,
  upsertItineraryItem as upsertItineraryItemAction,
} from "@/lib/trips/actions";

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

function statusFromResultErrorCode(code: string): number {
  switch (code) {
    case "unauthorized":
      return 401;
    case "forbidden":
      return 403;
    case "not_found":
      return 404;
    case "conflict":
      return 409;
    case "invalid_request":
      return 422;
    default:
      return 500;
  }
}

function apiCodeFromStatus(status: number): ApiErrorCode {
  if (status === 409) return "HTTP_409";
  if (status === 400) return "HTTP_400";
  return ApiError.codeFromStatus(status);
}

function toApiError(error: ResultError, endpoint: string): ApiError {
  const status = statusFromResultErrorCode(error.error);
  return new ApiError({
    code: apiCodeFromStatus(status),
    data: { error: error.error, issues: error.issues },
    endpoint,
    fieldErrors: error.fieldErrors,
    message: error.reason,
    status,
  });
}

function unwrapResult<T>(result: Result<T, ResultError>, endpoint: string): T {
  if (result.ok) return result.data;
  throw toApiError(result.error, endpoint);
}

function normalizeTripId(value: number | string | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : null;
}

function createOptimisticNumericId(): number {
  const parsed = Number.parseInt(secureId(8), 16);
  if (Number.isFinite(parsed) && parsed > 0) return -parsed;
  return -1;
}

function sortItinerary(items: ItineraryItem[]): ItineraryItem[] {
  return [...items].sort((a, b) => {
    const aStart = a.startAt ?? "";
    const bStart = b.startAt ?? "";
    if (aStart === bStart) return a.id - b.id;
    if (aStart === "") return 1;
    if (bStart === "") return -1;
    return aStart.localeCompare(bStart);
  });
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
      const suggestions = await makeAuthenticatedRequest<TripSuggestion[]>(
        "/api/trips/suggestions",
        { params: normalizedParams }
      );
      return suggestions;
    },
    queryKey: userId
      ? keys.trips.suggestion(userId, normalizedParams)
      : keys.trips.listDisabled(),
    staleTime: staleTimes.suggestions,
    throwOnError: false,
  });
}

/**
 * Hook to create a new trip.
 *
 * @returns Mutation object for creating trips with loading state and error handling.
 */
export function useCreateTrip() {
  const queryClient = useQueryClient();
  const userId = useCurrentUserId();

  return useMutation<UiTrip, AppError, TripCreateInput>({
    mutationFn: async (tripData: TripCreateInput) => {
      const result = await createTripAction(tripData);
      return unwrapResult(result, "trips.create");
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

/** Data structure for updating a trip. */
export type UpdateTripData = TripUpdateInput;

type UpdateTripContext = {
  detailKey?: QueryKey;
  previousDetail?: Trip | null;
  previousLists?: Array<[QueryKey, Trip[] | undefined]>;
};

/**
 * Hook to update an existing trip with an optimistic cache update.
 */
export function useUpdateTrip(options?: { userId?: string | null }) {
  const queryClient = useQueryClient();
  const inferredUserId = useCurrentUserId();
  const userId = options?.userId ?? inferredUserId;

  return useMutation<
    UiTrip,
    AppError,
    { tripId: string | number; data: UpdateTripData },
    UpdateTripContext
  >({
    mutationFn: async ({ tripId, data }) => {
      const numericTripId = normalizeTripId(tripId);
      if (numericTripId === null) {
        throw new ApiError({
          code: "VALIDATION_ERROR",
          message: "Invalid trip id",
          status: 422,
        });
      }

      const result = await updateTripAction(numericTripId, data);
      return unwrapResult(result, "trips.update");
    },
    onError: (_error, _vars, context) => {
      if (!userId) return;
      if (context?.detailKey && context.previousDetail) {
        queryClient.setQueryData(context.detailKey, context.previousDetail);
      }
      if (context?.previousLists) {
        for (const [key, value] of context.previousLists) {
          queryClient.setQueryData(key, value);
        }
      }
    },
    onMutate: async ({ tripId, data }) => {
      if (!userId) return {};

      const numericTripId = normalizeTripId(tripId);
      if (numericTripId === null) return {};

      const detailKey = keys.trips.detail(userId, numericTripId);
      const listPrefix = keys.trips.lists(userId);

      await queryClient.cancelQueries({ queryKey: detailKey });
      await queryClient.cancelQueries({ queryKey: listPrefix });

      const previousDetail = queryClient.getQueryData<Trip | null>(detailKey);
      const previousLists = queryClient.getQueriesData<Trip[]>({
        queryKey: listPrefix,
      });

      if (previousDetail) {
        queryClient.setQueryData<Trip>(detailKey, {
          ...previousDetail,
          ...data,
          updatedAt: nowIso(),
        });
      }

      queryClient.setQueriesData<Trip[]>({ queryKey: listPrefix }, (current) => {
        if (!current) return current;
        return current.map((trip) =>
          trip.id === String(numericTripId)
            ? { ...trip, ...data, updatedAt: nowIso() }
            : trip
        );
      });

      return { detailKey, previousDetail, previousLists };
    },
    onSuccess: (updated, vars) => {
      const numericTripId = normalizeTripId(vars.tripId);
      if (userId && numericTripId !== null) {
        queryClient.setQueryData(keys.trips.detail(userId, numericTripId), updated);
        queryClient.setQueriesData<Trip[]>(
          { queryKey: keys.trips.lists(userId) },
          (current) => {
            if (!current) return current;
            return current.map((trip) => (trip.id === updated.id ? updated : trip));
          }
        );
      }

      if (userId) {
        queryClient.invalidateQueries({ queryKey: keys.trips.lists(userId) });
        queryClient.invalidateQueries({ queryKey: keys.trips.user(userId) });
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
export function useDeleteTrip(options?: { userId?: string | null }) {
  const queryClient = useQueryClient();
  const inferredUserId = useCurrentUserId();
  const userId = options?.userId ?? inferredUserId;

  return useMutation<void, AppError, string | number>({
    mutationFn: async (tripId: string | number) => {
      const numericTripId = normalizeTripId(tripId);
      if (numericTripId === null) {
        throw new ApiError({
          code: "VALIDATION_ERROR",
          message: "Invalid trip id",
          status: 422,
        });
      }

      const result = await deleteTripAction(numericTripId);
      unwrapResult(result, "trips.delete");
    },
    onSuccess: (_data, tripId) => {
      const numericTripId = normalizeTripId(tripId);

      if (userId && numericTripId !== null) {
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
 * Converts filter values to API-compatible parameters for query keys.
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
        apiParams[key] = String(value);
      }
    }
  }

  return Object.keys(apiParams).length > 0 ? apiParams : undefined;
};

/**
 * Real-time connection status for trip subscriptions.
 *
 * Note: trips hooks no longer use Supabase realtime subscriptions directly; this
 * shape remains for backwards-compatible UI consumers.
 */
interface TripRealtimeStatus {
  /** Whether the real-time connection is active. */
  isConnected: boolean;
  /** Array of connection errors encountered. */
  errors: Error[];
}

const DEFAULT_REALTIME_STATUS: TripRealtimeStatus = {
  errors: [],
  isConnected: true,
};

/**
 * Hook to get user's trips.
 *
 * @param filters Optional filters to apply.
 */
export function useTrips(filters?: TripFilters, options?: { userId?: string | null }) {
  const inferredUserId = useCurrentUserId();
  const userId = options?.userId ?? inferredUserId;
  const apiParams = convertToApiParams(filters);

  const query = useQuery<Trip[], AppError>({
    enabled: !!userId,
    gcTime: cacheTimes.medium,
    queryFn: async () => {
      const result = await getTripsForUserAction(filters);
      return unwrapResult(result, "trips.get_list");
    },
    queryKey: userId ? keys.trips.list(userId, apiParams) : keys.trips.listDisabled(),
    staleTime: staleTimes.trips,
    throwOnError: false,
  });

  return {
    ...query,
    isConnected: DEFAULT_REALTIME_STATUS.isConnected,
    realtimeStatus: DEFAULT_REALTIME_STATUS,
  };
}

/**
 * Hook to fetch a single trip by ID.
 */
export function useTrip(
  tripId: string | number | null | undefined,
  options?: { userId?: string | null }
) {
  const inferredUserId = useCurrentUserId();
  const userId = options?.userId ?? inferredUserId;

  const numericTripId = normalizeTripId(tripId);

  const query = useQuery<Trip | null, AppError>({
    enabled: numericTripId !== null && !!userId,
    gcTime: cacheTimes.medium,
    queryFn: async () => {
      if (numericTripId === null) return null;
      const result = await getTripByIdAction(numericTripId);
      return unwrapResult(result, "trips.get_detail");
    },
    queryKey:
      numericTripId !== null && userId
        ? keys.trips.detail(userId, numericTripId)
        : keys.trips.detailDisabled(),
    staleTime: staleTimes.trips,
    throwOnError: false,
  });

  return {
    ...query,
    isConnected: DEFAULT_REALTIME_STATUS.isConnected,
    realtimeStatus: DEFAULT_REALTIME_STATUS,
  };
}

export function useTripItinerary(
  tripId: number | null,
  options?: { userId?: string | null }
) {
  const inferredUserId = useCurrentUserId();
  const userId = options?.userId ?? inferredUserId;
  const enabled = tripId !== null && !!userId;
  const queryKey =
    tripId !== null && userId
      ? keys.trips.itinerary(userId, tripId)
      : keys.trips.itineraryDisabled();

  return useQuery<ItineraryItem[], AppError>({
    enabled,
    gcTime: cacheTimes.medium,
    queryFn: async () => {
      if (tripId === null) {
        throw new ApiError({
          code: "VALIDATION_ERROR",
          message: "Trip id is required",
          status: 422,
        });
      }

      const result = await getTripItineraryAction(tripId);
      return unwrapResult(result, "trips.itinerary.list");
    },
    queryKey,
    staleTime: staleTimes.realtime,
    throwOnError: false,
  });
}

type UpsertItineraryContext = {
  optimisticId?: number;
  previous?: ItineraryItem[];
};

export function useUpsertTripItineraryItem(
  tripId: number,
  options?: { userId?: string | null }
) {
  const queryClient = useQueryClient();
  const inferredUserId = useCurrentUserId();
  const userId = options?.userId ?? inferredUserId;

  return useMutation<
    ItineraryItem,
    AppError,
    ItineraryItemUpsertInput,
    UpsertItineraryContext
  >({
    mutationFn: async (input) => {
      const result = await upsertItineraryItemAction(tripId, input);
      return unwrapResult(result, "trips.itinerary.upsert");
    },
    onError: (_error, _vars, context) => {
      if (!userId) return;
      const key = keys.trips.itinerary(userId, tripId);
      if (context?.previous) {
        queryClient.setQueryData(key, context.previous);
      }
    },
    onMutate: async (input) => {
      if (!userId) return {};

      const key = keys.trips.itinerary(userId, tripId);
      await queryClient.cancelQueries({ queryKey: key });

      const previous = queryClient.getQueryData<ItineraryItem[]>(key);

      if (!previous) {
        if (input.id === undefined) {
          const optimisticId = createOptimisticNumericId();
          const optimistic: ItineraryItem = {
            ...input,
            createdAt: nowIso(),
            createdBy: userId,
            id: optimisticId,
            tripId,
            updatedAt: nowIso(),
          };
          queryClient.setQueryData(key, sortItinerary([optimistic]));
          return { optimisticId, previous };
        }

        return { previous };
      }

      if (input.id === undefined) {
        const optimisticId = createOptimisticNumericId();
        const optimistic: ItineraryItem = {
          ...input,
          createdAt: nowIso(),
          createdBy: userId,
          id: optimisticId,
          tripId,
          updatedAt: nowIso(),
        };
        queryClient.setQueryData(key, sortItinerary([...previous, optimistic]));
        return { optimisticId, previous };
      }

      queryClient.setQueryData(
        key,
        sortItinerary(
          previous.map((item) =>
            item.id === input.id ? { ...item, ...input, updatedAt: nowIso() } : item
          )
        )
      );

      return { previous };
    },
    onSettled: () => {
      if (!userId) return;
      queryClient.invalidateQueries({ queryKey: keys.trips.itinerary(userId, tripId) });
    },
    onSuccess: (item, _vars, context) => {
      if (!userId) return;
      const key = keys.trips.itinerary(userId, tripId);

      queryClient.setQueryData<ItineraryItem[]>(key, (current) => {
        const list = current ?? [];

        if (context?.optimisticId) {
          return sortItinerary(
            list.map((existing) =>
              existing.id === context.optimisticId ? item : existing
            )
          );
        }

        return sortItinerary(
          list.map((existing) => (existing.id === item.id ? item : existing))
        );
      });
    },
    throwOnError: false,
  });
}

export function useDeleteTripItineraryItem(
  tripId: number,
  options?: { userId?: string | null }
) {
  const queryClient = useQueryClient();
  const inferredUserId = useCurrentUserId();
  const userId = options?.userId ?? inferredUserId;

  return useMutation<
    void,
    AppError,
    { itemId: number },
    { previous?: ItineraryItem[] }
  >({
    mutationFn: async ({ itemId }) => {
      const result = await deleteItineraryItemAction(tripId, itemId);
      unwrapResult(result, "trips.itinerary.delete");
    },
    onError: (_error, _vars, context) => {
      if (!userId) return;
      const key = keys.trips.itinerary(userId, tripId);
      if (context?.previous) {
        queryClient.setQueryData(key, context.previous);
      }
    },
    onMutate: async ({ itemId }) => {
      if (!userId) return {};

      const key = keys.trips.itinerary(userId, tripId);
      await queryClient.cancelQueries({ queryKey: key });
      const previous = queryClient.getQueryData<ItineraryItem[]>(key);

      if (previous) {
        queryClient.setQueryData(
          key,
          previous.filter((item) => item.id !== itemId)
        );
      }

      return { previous };
    },
    onSettled: () => {
      if (!userId) return;
      queryClient.invalidateQueries({ queryKey: keys.trips.itinerary(userId, tripId) });
    },
    throwOnError: false,
  });
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
 * @returns Query object containing upcoming flights data.
 */
export function useUpcomingFlights(params?: UpcomingFlightsParams) {
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  const normalizedParams = {
    limit: params?.limit ?? 10,
  };

  return useQuery<UpcomingFlight[], AppError>({
    gcTime: cacheTimes.short,
    queryFn: async () => {
      return await makeAuthenticatedRequest<UpcomingFlight[]>("/api/flights/upcoming", {
        params: normalizedParams,
      });
    },
    queryKey: keys.external.upcomingFlights(normalizedParams),
    refetchInterval: 2 * 60 * 1000,
    refetchIntervalInBackground: false,
    staleTime: staleTimes.realtime,
    throwOnError: false,
  });
}
