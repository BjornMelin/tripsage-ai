/**
 * @fileoverview Query factory functions for consistent query creation and
 * management. Encodes caching, staleness, and invalidation patterns.
 */

import type {
  QueryClient,
  UseInfiniteQueryOptions,
  UseMutationOptions,
  UseQueryOptions,
} from "@tanstack/react-query";
import type { AppError } from "@/lib/api/error-types";
import { cacheTimes, queryKeys, staleTimes } from "@/lib/query-keys";

/**
 * Base query factory interface
 */
interface BaseQueryFactory<Data, Error = AppError> {
  queryKey: readonly unknown[];
  queryFn: () => Promise<Data>;
  options?: Omit<UseQueryOptions<Data, Error>, "queryKey" | "queryFn">;
}

/**
 * Base mutation factory interface
 */
interface BaseMutationFactory<Data, Variables, Error = AppError> {
  mutationFn: (variables: Variables) => Promise<Data>;
  options?: Omit<UseMutationOptions<Data, Error, Variables>, "mutationFn">;
}

/**
 * Trip-related query factories
 */
export const tripQueries = {
  /**
   * Factory for fetching all trips
   */
  all: (
    apiCall: (filters?: Record<string, unknown>) => Promise<unknown[]>,
    filters?: Record<string, unknown>
  ): BaseQueryFactory<unknown[]> => ({
    options: {
      gcTime: cacheTimes.medium,
      retry: (failureCount, error) => {
        if (error instanceof Error && "status" in error) {
          const status = (error as Error & { status?: number }).status;
          if (status === 401 || status === 403) return false;
        }
        return failureCount < 2;
      },
      staleTime: staleTimes.trips,
    },
    queryFn: () => apiCall(filters),
    queryKey: queryKeys.trips.list(filters),
  }),

  /**
   * Factory for fetching a single trip
   */
  detail: (
    apiCall: (id: number) => Promise<unknown>,
    tripId: number
  ): BaseQueryFactory<unknown> => ({
    options: {
      enabled: !!tripId,
      gcTime: cacheTimes.medium,
      retry: (failureCount, error) => {
        if (error instanceof Error && "status" in error) {
          const status = (error as Error & { status?: number }).status;
          if (status === 404 || status === 401 || status === 403) return false;
        }
        return failureCount < 2;
      },
      staleTime: staleTimes.trips,
    },
    queryFn: () => apiCall(tripId),
    queryKey: queryKeys.trips.detail(tripId),
  }),

  /**
   * Factory for trip suggestions
   */
  suggestions: (
    apiCall: (params?: Record<string, unknown>) => Promise<unknown[]>,
    params?: Record<string, unknown>
  ): BaseQueryFactory<unknown[]> => ({
    options: {
      gcTime: cacheTimes.medium,
      retry: 2,
      staleTime: staleTimes.suggestions,
    },
    queryFn: () => apiCall(params),
    queryKey: queryKeys.trips.suggestions(params),
  }),
};

/**
 * Chat-related query factories
 */
export const chatQueries = {
  /**
   * Factory for chat messages (infinite query)
   */
  messages: (
    apiCall: (sessionId: string, pageParam?: number) => Promise<unknown>,
    sessionId: string
  ): Omit<UseInfiniteQueryOptions<unknown, AppError>, "queryKey" | "queryFn"> & {
    queryKey: readonly unknown[];
    queryFn: ({ pageParam }: { pageParam: number }) => Promise<unknown>;
  } => ({
    enabled: !!sessionId,
    gcTime: cacheTimes.short,
    getNextPageParam: (lastPage: unknown) =>
      (lastPage as { nextCursor?: number }).nextCursor,
    initialPageParam: 0,
    queryFn: ({ pageParam = 0 }) => apiCall(sessionId, pageParam),
    queryKey: queryKeys.chat.messages(sessionId),
    staleTime: staleTimes.chat,
  }),
  /**
   * Factory for chat sessions
   */
  sessions: (
    apiCall: (tripId?: number) => Promise<unknown[]>,
    tripId?: number
  ): BaseQueryFactory<unknown[]> => ({
    options: {
      gcTime: cacheTimes.short,
      staleTime: staleTimes.chat,
    },
    queryFn: () => apiCall(tripId),
    queryKey: queryKeys.chat.sessionList(tripId),
  }),

  /**
   * Factory for chat statistics
   */
  stats: (
    apiCall: (userId: string) => Promise<unknown>,
    userId: string
  ): BaseQueryFactory<unknown> => ({
    options: {
      enabled: !!userId,
      gcTime: cacheTimes.long,
      staleTime: staleTimes.stats,
    },
    queryFn: () => apiCall(userId),
    queryKey: queryKeys.chat.stats(userId),
  }),
};

/**
 * Search-related query factories
 */
export const searchQueries = {
  /**
   * Factory for accommodation searches
   */
  accommodations: (
    apiCall: (params: Record<string, unknown>) => Promise<unknown>,
    params: Record<string, unknown>
  ): BaseQueryFactory<unknown> => ({
    options: {
      enabled: Object.keys(params).length > 0,
      gcTime: cacheTimes.short,
      staleTime: staleTimes.search,
    },
    queryFn: () => apiCall(params),
    queryKey: queryKeys.search.accommodations(params),
  }),
  /**
   * Factory for flight searches
   */
  flights: (
    apiCall: (params: Record<string, unknown>) => Promise<unknown>,
    params: Record<string, unknown>
  ): BaseQueryFactory<unknown> => ({
    options: {
      enabled: Object.keys(params).length > 0,
      gcTime: cacheTimes.short,
      staleTime: staleTimes.search,
    },
    queryFn: () => apiCall(params),
    queryKey: queryKeys.search.flights(params),
  }),

  /**
   * Factory for search suggestions
   */
  suggestions: (
    apiCall: () => Promise<unknown[]>,
    type: "flights" | "accommodations" | "activities" | "destinations"
  ): BaseQueryFactory<unknown[]> => ({
    options: {
      gcTime: cacheTimes.long,
      staleTime: staleTimes.suggestions,
    },
    queryFn: apiCall,
    queryKey: queryKeys.search.suggestions(type),
  }),
};

/**
 * File-related query factories
 */
export const fileQueries = {
  /**
   * Factory for file attachments
   */
  attachments: (
    apiCall: (filters?: Record<string, unknown>) => Promise<unknown[]>,
    filters?: Record<string, unknown>
  ): BaseQueryFactory<unknown[]> => ({
    options: {
      gcTime: cacheTimes.medium,
      staleTime: staleTimes.files,
    },
    queryFn: () => apiCall(filters),
    queryKey: queryKeys.files.attachments(filters),
  }),

  /**
   * Factory for storage statistics
   */
  stats: (
    apiCall: (userId: string) => Promise<unknown>,
    userId: string
  ): BaseQueryFactory<unknown> => ({
    options: {
      enabled: !!userId,
      gcTime: cacheTimes.long,
      staleTime: staleTimes.stats,
    },
    queryFn: () => apiCall(userId),
    queryKey: queryKeys.files.stats(userId),
  }),
};

/**
 * Mutation factories
 */
export const mutationFactories = {
  /**
   * Chat mutations
   */
  chat: {
    createSession: (
      apiCall: (data: unknown) => Promise<unknown>
    ): BaseMutationFactory<unknown, unknown> => ({
      mutationFn: apiCall,
      options: {
        onSuccess: (_data, _variables, context) => {
          const queryClient = context as QueryClient;
          queryClient.invalidateQueries({ queryKey: queryKeys.chat.sessions() });
        },
        retry: 1,
      },
    }),

    sendMessage: (
      apiCall: (data: { sessionId: string; content: string }) => Promise<unknown>
    ): BaseMutationFactory<unknown, { sessionId: string; content: string }> => ({
      mutationFn: apiCall,
      options: {
        onError: (_err, variables, context) => {
          if (
            context &&
            typeof context === "object" &&
            context !== null &&
            "previousMessages" in context &&
            context.previousMessages
          ) {
            const queryClient = {} as QueryClient; // Would be injected
            queryClient.setQueryData(
              queryKeys.chat.messages(variables.sessionId),
              context.previousMessages
            );
          }
        },
        onMutate: async (variables) => {
          const queryClient = {} as QueryClient; // Would be injected
          await queryClient.cancelQueries({
            queryKey: queryKeys.chat.messages(variables.sessionId),
          });

          const previousMessages = queryClient.getQueryData(
            queryKeys.chat.messages(variables.sessionId)
          );

          // Optimistic update would go here

          return { previousMessages };
        },
        onSettled: (_data, _error, variables) => {
          const queryClient = {} as QueryClient; // Would be injected
          queryClient.invalidateQueries({
            queryKey: queryKeys.chat.messages(variables.sessionId),
          });
        },
        retry: 1,
      },
    }),
  },

  /**
   * File mutations
   */
  files: {
    delete: (
      apiCall: (id: string) => Promise<void>
    ): BaseMutationFactory<void, string> => ({
      mutationFn: apiCall,
      options: {
        onSuccess: (_data, variables, context) => {
          const queryClient = context as QueryClient;
          queryClient.invalidateQueries({ queryKey: queryKeys.files.all() });
          queryClient.invalidateQueries({ queryKey: queryKeys.files.stats("") });
          queryClient.removeQueries({
            queryKey: queryKeys.files.attachment(variables),
          });
        },
        retry: 1,
      },
    }),
    upload: (
      apiCall: (file: File) => Promise<unknown>
    ): BaseMutationFactory<unknown, File> => ({
      mutationFn: apiCall,
      options: {
        onSuccess: (_data, _variables, context) => {
          const queryClient = context as QueryClient;
          queryClient.invalidateQueries({ queryKey: queryKeys.files.all() });
          queryClient.invalidateQueries({ queryKey: queryKeys.files.stats("") });
        },
        retry: 1,
      },
    }),
  },
  /**
   * Trip mutations
   */
  trips: {
    create: (
      apiCall: (data: unknown) => Promise<unknown>
    ): BaseMutationFactory<unknown, unknown> => ({
      mutationFn: apiCall,
      options: {
        onSuccess: (_data, _variables, context) => {
          const queryClient = context as QueryClient;
          queryClient.invalidateQueries({ queryKey: queryKeys.trips.all() });
          queryClient.invalidateQueries({ queryKey: queryKeys.trips.suggestions() });
        },
        retry: 1,
      },
    }),

    delete: (
      apiCall: (id: number) => Promise<void>
    ): BaseMutationFactory<void, number> => ({
      mutationFn: apiCall,
      options: {
        onSuccess: (_data, variables, context) => {
          const queryClient = context as QueryClient;
          queryClient.invalidateQueries({ queryKey: queryKeys.trips.all() });
          queryClient.removeQueries({ queryKey: queryKeys.trips.detail(variables) });
        },
        retry: 1,
      },
    }),

    update: (
      apiCall: (data: { id: number; updates: unknown }) => Promise<unknown>
    ): BaseMutationFactory<unknown, { id: number; updates: unknown }> => ({
      mutationFn: apiCall,
      options: {
        onSuccess: (_data, variables, context) => {
          const queryClient = context as QueryClient;
          queryClient.invalidateQueries({ queryKey: queryKeys.trips.all() });
          queryClient.invalidateQueries({
            queryKey: queryKeys.trips.detail(variables.id),
          });
        },
        retry: 1,
      },
    }),
  },
};

/**
 * Utility function to create prefetch queries
 */
export const createPrefetchQuery = (
  queryClient: QueryClient,
  factory: BaseQueryFactory<unknown>
) => {
  return queryClient.prefetchQuery({
    queryFn: factory.queryFn,
    queryKey: factory.queryKey,
    ...factory.options,
  });
};

/**
 * Utility function to create query invalidation patterns
 */
export const queryInvalidation = {
  /**
   * Invalidate all search queries
   */
  allSearch: (queryClient: QueryClient) => {
    queryClient.invalidateQueries({ queryKey: queryKeys.search.all() });
  },
  /**
   * Invalidate all trip-related queries
   */
  allTrips: (queryClient: QueryClient) => {
    queryClient.invalidateQueries({ queryKey: queryKeys.trips.all() });
  },

  /**
   * Invalidate all chat queries for a session
   */
  chatSession: (queryClient: QueryClient, sessionId: string) => {
    queryClient.invalidateQueries({ queryKey: queryKeys.chat.session(sessionId) });
    queryClient.invalidateQueries({ queryKey: queryKeys.chat.messages(sessionId) });
  },

  /**
   * Invalidate specific trip
   */
  trip: (queryClient: QueryClient, tripId: number) => {
    queryClient.invalidateQueries({ queryKey: queryKeys.trips.detail(tripId) });
  },
};

/**
 * Type helpers for factory usage
 */
export type QueryFactory<Data> = BaseQueryFactory<Data>;
export type MutationFactory<Data, Variables> = BaseMutationFactory<Data, Variables>;
