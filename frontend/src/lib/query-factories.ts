/**
 * Query factory functions for consistent query creation and management
 * Following React Query v5 best practices for query organization
 */

import { type AppError } from "@/lib/api/error-types";
import { queryKeys, staleTimes, cacheTimes } from "@/lib/query-keys";
import type {
  UseQueryOptions,
  UseMutationOptions,
  UseInfiniteQueryOptions,
  QueryClient,
} from "@tanstack/react-query";

/**
 * Base query factory interface
 */
interface BaseQueryFactory<TData, TError = AppError> {
  queryKey: readonly unknown[];
  queryFn: () => Promise<TData>;
  options?: Omit<UseQueryOptions<TData, TError>, "queryKey" | "queryFn">;
}

/**
 * Base mutation factory interface
 */
interface BaseMutationFactory<TData, TVariables, TError = AppError> {
  mutationFn: (variables: TVariables) => Promise<TData>;
  options?: Omit<UseMutationOptions<TData, TError, TVariables>, "mutationFn">;
}

/**
 * Trip-related query factories
 */
export const tripQueries = {
  /**
   * Factory for fetching all trips
   */
  all: (
    apiCall: (filters?: Record<string, unknown>) => Promise<any[]>,
    filters?: Record<string, unknown>
  ): BaseQueryFactory<any[]> => ({
    queryKey: queryKeys.trips.list(filters),
    queryFn: () => apiCall(filters),
    options: {
      staleTime: staleTimes.trips,
      gcTime: cacheTimes.medium,
      retry: (failureCount, error) => {
        if (error instanceof Error && "status" in error) {
          const status = (error as any).status;
          if (status === 401 || status === 403) return false;
        }
        return failureCount < 2;
      },
    },
  }),

  /**
   * Factory for fetching a single trip
   */
  detail: (
    apiCall: (id: number) => Promise<any>,
    tripId: number
  ): BaseQueryFactory<any> => ({
    queryKey: queryKeys.trips.detail(tripId),
    queryFn: () => apiCall(tripId),
    options: {
      staleTime: staleTimes.trips,
      gcTime: cacheTimes.medium,
      enabled: !!tripId,
      retry: (failureCount, error) => {
        if (error instanceof Error && "status" in error) {
          const status = (error as any).status;
          if (status === 404 || status === 401 || status === 403) return false;
        }
        return failureCount < 2;
      },
    },
  }),

  /**
   * Factory for trip suggestions
   */
  suggestions: (
    apiCall: (params?: Record<string, unknown>) => Promise<any[]>,
    params?: Record<string, unknown>
  ): BaseQueryFactory<any[]> => ({
    queryKey: queryKeys.trips.suggestions(params),
    queryFn: () => apiCall(params),
    options: {
      staleTime: staleTimes.suggestions,
      gcTime: cacheTimes.medium,
      retry: 2,
    },
  }),
};

/**
 * Chat-related query factories
 */
export const chatQueries = {
  /**
   * Factory for chat sessions
   */
  sessions: (
    apiCall: (tripId?: number) => Promise<any[]>,
    tripId?: number
  ): BaseQueryFactory<any[]> => ({
    queryKey: queryKeys.chat.sessionList(tripId),
    queryFn: () => apiCall(tripId),
    options: {
      staleTime: staleTimes.chat,
      gcTime: cacheTimes.short,
    },
  }),

  /**
   * Factory for chat messages (infinite query)
   */
  messages: (
    apiCall: (sessionId: string, pageParam?: number) => Promise<any>,
    sessionId: string
  ): Omit<UseInfiniteQueryOptions<any, AppError>, "queryKey" | "queryFn"> & {
    queryKey: readonly unknown[];
    queryFn: any;
  } => ({
    queryKey: queryKeys.chat.messages(sessionId),
    queryFn: ({ pageParam = 0 }) => apiCall(sessionId, pageParam),
    initialPageParam: 0,
    getNextPageParam: (lastPage: any) => lastPage.nextCursor,
    staleTime: staleTimes.chat,
    gcTime: cacheTimes.short,
    enabled: !!sessionId,
  }),

  /**
   * Factory for chat statistics
   */
  stats: (
    apiCall: (userId: string) => Promise<any>,
    userId: string
  ): BaseQueryFactory<any> => ({
    queryKey: queryKeys.chat.stats(userId),
    queryFn: () => apiCall(userId),
    options: {
      staleTime: staleTimes.stats,
      gcTime: cacheTimes.long,
      enabled: !!userId,
    },
  }),
};

/**
 * Search-related query factories
 */
export const searchQueries = {
  /**
   * Factory for flight searches
   */
  flights: (
    apiCall: (params: Record<string, unknown>) => Promise<any>,
    params: Record<string, unknown>
  ): BaseQueryFactory<any> => ({
    queryKey: queryKeys.search.flights(params),
    queryFn: () => apiCall(params),
    options: {
      staleTime: staleTimes.search,
      gcTime: cacheTimes.short,
      enabled: Object.keys(params).length > 0,
    },
  }),

  /**
   * Factory for accommodation searches
   */
  accommodations: (
    apiCall: (params: Record<string, unknown>) => Promise<any>,
    params: Record<string, unknown>
  ): BaseQueryFactory<any> => ({
    queryKey: queryKeys.search.accommodations(params),
    queryFn: () => apiCall(params),
    options: {
      staleTime: staleTimes.search,
      gcTime: cacheTimes.short,
      enabled: Object.keys(params).length > 0,
    },
  }),

  /**
   * Factory for search suggestions
   */
  suggestions: (
    apiCall: () => Promise<any[]>,
    type: "flights" | "accommodations" | "activities" | "destinations"
  ): BaseQueryFactory<any[]> => ({
    queryKey: queryKeys.search.suggestions(type),
    queryFn: apiCall,
    options: {
      staleTime: staleTimes.suggestions,
      gcTime: cacheTimes.long,
    },
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
    apiCall: (filters?: Record<string, unknown>) => Promise<any[]>,
    filters?: Record<string, unknown>
  ): BaseQueryFactory<any[]> => ({
    queryKey: queryKeys.files.attachments(filters),
    queryFn: () => apiCall(filters),
    options: {
      staleTime: staleTimes.files,
      gcTime: cacheTimes.medium,
    },
  }),

  /**
   * Factory for storage statistics
   */
  stats: (
    apiCall: (userId: string) => Promise<any>,
    userId: string
  ): BaseQueryFactory<any> => ({
    queryKey: queryKeys.files.stats(userId),
    queryFn: () => apiCall(userId),
    options: {
      staleTime: staleTimes.stats,
      gcTime: cacheTimes.long,
      enabled: !!userId,
    },
  }),
};

/**
 * Mutation factories
 */
export const mutationFactories = {
  /**
   * Trip mutations
   */
  trips: {
    create: (apiCall: (data: any) => Promise<any>): BaseMutationFactory<any, any> => ({
      mutationFn: apiCall,
      options: {
        onSuccess: (data, variables, context) => {
          const queryClient = context as QueryClient;
          queryClient.invalidateQueries({ queryKey: queryKeys.trips.all() });
          queryClient.invalidateQueries({ queryKey: queryKeys.trips.suggestions() });
        },
        retry: 1,
      },
    }),

    update: (
      apiCall: (data: { id: number; updates: any }) => Promise<any>
    ): BaseMutationFactory<any, { id: number; updates: any }> => ({
      mutationFn: apiCall,
      options: {
        onSuccess: (data, variables, context) => {
          const queryClient = context as QueryClient;
          queryClient.invalidateQueries({ queryKey: queryKeys.trips.all() });
          queryClient.invalidateQueries({
            queryKey: queryKeys.trips.detail(variables.id),
          });
        },
        retry: 1,
      },
    }),

    delete: (
      apiCall: (id: number) => Promise<void>
    ): BaseMutationFactory<void, number> => ({
      mutationFn: apiCall,
      options: {
        onSuccess: (data, variables, context) => {
          const queryClient = context as QueryClient;
          queryClient.invalidateQueries({ queryKey: queryKeys.trips.all() });
          queryClient.removeQueries({ queryKey: queryKeys.trips.detail(variables) });
        },
        retry: 1,
      },
    }),
  },

  /**
   * Chat mutations
   */
  chat: {
    createSession: (
      apiCall: (data: any) => Promise<any>
    ): BaseMutationFactory<any, any> => ({
      mutationFn: apiCall,
      options: {
        onSuccess: (data, variables, context) => {
          const queryClient = context as QueryClient;
          queryClient.invalidateQueries({ queryKey: queryKeys.chat.sessions() });
        },
        retry: 1,
      },
    }),

    sendMessage: (
      apiCall: (data: { sessionId: string; content: string }) => Promise<any>
    ): BaseMutationFactory<any, { sessionId: string; content: string }> => ({
      mutationFn: apiCall,
      options: {
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
        onError: (err, variables, context) => {
          if (context?.previousMessages) {
            const queryClient = {} as QueryClient; // Would be injected
            queryClient.setQueryData(
              queryKeys.chat.messages(variables.sessionId),
              context.previousMessages
            );
          }
        },
        onSettled: (data, error, variables) => {
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
    upload: (
      apiCall: (file: File) => Promise<any>
    ): BaseMutationFactory<any, File> => ({
      mutationFn: apiCall,
      options: {
        onSuccess: (data, variables, context) => {
          const queryClient = context as QueryClient;
          queryClient.invalidateQueries({ queryKey: queryKeys.files.all() });
          queryClient.invalidateQueries({ queryKey: queryKeys.files.stats("") });
        },
        retry: 1,
      },
    }),

    delete: (
      apiCall: (id: string) => Promise<void>
    ): BaseMutationFactory<void, string> => ({
      mutationFn: apiCall,
      options: {
        onSuccess: (data, variables, context) => {
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
  },
};

/**
 * Utility function to create prefetch queries
 */
export const createPrefetchQuery = (
  queryClient: QueryClient,
  factory: BaseQueryFactory<any>
) => {
  return queryClient.prefetchQuery({
    queryKey: factory.queryKey,
    queryFn: factory.queryFn,
    ...factory.options,
  });
};

/**
 * Utility function to create query invalidation patterns
 */
export const queryInvalidation = {
  /**
   * Invalidate all trip-related queries
   */
  allTrips: (queryClient: QueryClient) => {
    queryClient.invalidateQueries({ queryKey: queryKeys.trips.all() });
  },

  /**
   * Invalidate specific trip
   */
  trip: (queryClient: QueryClient, tripId: number) => {
    queryClient.invalidateQueries({ queryKey: queryKeys.trips.detail(tripId) });
  },

  /**
   * Invalidate all chat queries for a session
   */
  chatSession: (queryClient: QueryClient, sessionId: string) => {
    queryClient.invalidateQueries({ queryKey: queryKeys.chat.session(sessionId) });
    queryClient.invalidateQueries({ queryKey: queryKeys.chat.messages(sessionId) });
  },

  /**
   * Invalidate all search queries
   */
  allSearch: (queryClient: QueryClient) => {
    queryClient.invalidateQueries({ queryKey: queryKeys.search.all() });
  },
};

/**
 * Type helpers for factory usage
 */
export type QueryFactory<TData> = BaseQueryFactory<TData>;
export type MutationFactory<TData, TVariables> = BaseMutationFactory<TData, TVariables>;
