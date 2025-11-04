"use client";

import { QueryCache, QueryClient } from "@tanstack/react-query";

// Error handling for query cache
const QUERY_CACHE = new QueryCache({
  onError: (error, query) => {
    // Log errors for debugging
    console.error(`Query failed for key: ${JSON.stringify(query.queryKey)}`, error);

    // Report critical errors in production
    if (process.env.NODE_ENV === "production") {
      // You could send to error reporting service here
      console.warn("Query error reported to monitoring");
    }
  },
});

// Create optimized query client with performance-focused defaults
export const createOptimizedQueryClient = () => {
  return new QueryClient({
    defaultOptions: {
      mutations: {
        // Retry failed mutations only once
        retry: 1,
        retryDelay: 1000,
      },
      queries: {
        gcTime: 10 * 60 * 1000, // 10 minutes (renamed from cacheTime in v5)
        refetchInterval: false, // Disable automatic polling by default
        refetchOnReconnect: "always", // Ensure fresh data on reconnect

        // Performance optimizations
        refetchOnWindowFocus: false, // Reduce unnecessary requests

        // Retry configuration
        retry: (failureCount, error: unknown) => {
          // Don't retry for client errors (4xx)
          const httpError = error as { status?: number };
          if (httpError?.status && httpError.status >= 400 && httpError.status < 500) {
            return false;
          }
          // Retry up to 3 times for server errors
          return failureCount < 3;
        },
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
        // Stale while revalidate strategy - serve cached data while fetching fresh data
        staleTime: 5 * 60 * 1000, // 5 minutes
      },
    },
    queryCache: QUERY_CACHE,
  });
};

// Cache invalidation utilities
export const cacheUtils = {
  // Clear all cached data (use sparingly)
  clearAll: (queryClient: QueryClient) => {
    queryClient.clear();
  },
  // Invalidate all queries for a specific resource
  invalidateResource: (queryClient: QueryClient, resource: string) => {
    queryClient.invalidateQueries({
      predicate: (query) =>
        Array.isArray(query.queryKey) && query.queryKey[0] === resource,
    });
  },

  // Prefetch critical data
  prefetchCritical: async (queryClient: QueryClient) => {
    // Prefetch user profile and common data
    const criticalQueries = [
      { enabled: false, queryKey: ["user", "profile"] },
      { enabled: false, queryKey: ["trips", "recent"] },
    ];

    await Promise.allSettled(
      criticalQueries.map((query) =>
        queryClient.prefetchQuery({
          ...query,
          staleTime: 10 * 60 * 1000, // 10 minutes for critical data
        })
      )
    );
  },

  // Optimistically update cache for better UX
  updateCache: <T>(
    queryClient: QueryClient,
    queryKey: unknown[],
    updater: (oldData: T | undefined) => T
  ) => {
    queryClient.setQueryData(queryKey, updater);
  },
};

// Query key factories for consistency
export const queryKeys = {
  // Agent-related queries
  agents: {
    all: ["agents"] as const,
    metrics: (agentId: string) => ["agents", "metrics", agentId] as const,
    status: () => ["agents", "status"] as const,
  },

  // Chat-related queries
  chat: {
    all: ["chat"] as const,
    messages: (sessionId: string) => ["chat", "messages", sessionId] as const,
    session: (id: string) => ["chat", "session", id] as const,
    sessions: () => ["chat", "sessions"] as const,
  },

  // Search-related queries
  search: {
    activities: (params: Record<string, unknown>) =>
      ["search", "activities", params] as const,
    all: ["search"] as const,
    destinations: (query: string) => ["search", "destinations", query] as const,
    flights: (params: Record<string, unknown>) =>
      ["search", "flights", params] as const,
    hotels: (params: Record<string, unknown>) => ["search", "hotels", params] as const,
  },

  // Trip-related queries
  trips: {
    all: ["trips"] as const,
    details: (id: string) => ["trips", "detail", id] as const,
    list: (filters: Record<string, unknown>) => ["trips", "list", filters] as const,
    lists: () => ["trips", "list"] as const,
    recent: () => ["trips", "recent"] as const,
  },
  // User-related queries
  user: {
    all: ["user"] as const,
    apiKeys: () => ["user", "api-keys"] as const,
    profile: () => ["user", "profile"] as const,
    settings: () => ["user", "settings"] as const,
  },
};
