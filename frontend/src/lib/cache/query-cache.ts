"use client";

import { QueryCache, QueryClient } from "@tanstack/react-query";

// Enhanced error handling for query cache
const queryCache = new QueryCache({
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
    queryCache,
    defaultOptions: {
      queries: {
        // Stale while revalidate strategy - serve cached data while fetching fresh data
        staleTime: 5 * 60 * 1000, // 5 minutes
        gcTime: 10 * 60 * 1000, // 10 minutes (renamed from cacheTime in v5)

        // Performance optimizations
        refetchOnWindowFocus: false, // Reduce unnecessary requests
        refetchOnReconnect: "always", // Ensure fresh data on reconnect
        refetchInterval: false, // Disable automatic polling by default

        // Retry configuration
        retry: (failureCount, error: any) => {
          // Don't retry for client errors (4xx)
          if (error?.status >= 400 && error?.status < 500) {
            return false;
          }
          // Retry up to 3 times for server errors
          return failureCount < 3;
        },
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      },
      mutations: {
        // Retry failed mutations only once
        retry: 1,
        retryDelay: 1000,
      },
    },
  });
};

// Cache invalidation utilities
export const cacheUtils = {
  // Invalidate all queries for a specific resource
  invalidateResource: (queryClient: QueryClient, resource: string) => {
    queryClient.invalidateQueries({
      predicate: (query) =>
        Array.isArray(query.queryKey) && query.queryKey[0] === resource,
    });
  },

  // Optimistically update cache for better UX
  updateCache: <T>(
    queryClient: QueryClient,
    queryKey: unknown[],
    updater: (oldData: T | undefined) => T
  ) => {
    queryClient.setQueryData(queryKey, updater);
  },

  // Clear all cached data (use sparingly)
  clearAll: (queryClient: QueryClient) => {
    queryClient.clear();
  },

  // Prefetch critical data
  prefetchCritical: async (queryClient: QueryClient) => {
    // Prefetch user profile and common data
    const criticalQueries = [
      { queryKey: ["user", "profile"], enabled: false },
      { queryKey: ["trips", "recent"], enabled: false },
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
};

// Query key factories for consistency
export const queryKeys = {
  // User-related queries
  user: {
    all: ["user"] as const,
    profile: () => ["user", "profile"] as const,
    settings: () => ["user", "settings"] as const,
    apiKeys: () => ["user", "api-keys"] as const,
  },

  // Trip-related queries
  trips: {
    all: ["trips"] as const,
    lists: () => ["trips", "list"] as const,
    list: (filters: Record<string, unknown>) => ["trips", "list", filters] as const,
    details: (id: string) => ["trips", "detail", id] as const,
    recent: () => ["trips", "recent"] as const,
  },

  // Search-related queries
  search: {
    all: ["search"] as const,
    flights: (params: Record<string, unknown>) =>
      ["search", "flights", params] as const,
    hotels: (params: Record<string, unknown>) => ["search", "hotels", params] as const,
    activities: (params: Record<string, unknown>) =>
      ["search", "activities", params] as const,
    destinations: (query: string) => ["search", "destinations", query] as const,
  },

  // Chat-related queries
  chat: {
    all: ["chat"] as const,
    sessions: () => ["chat", "sessions"] as const,
    session: (id: string) => ["chat", "session", id] as const,
    messages: (sessionId: string) => ["chat", "messages", sessionId] as const,
  },

  // Agent-related queries
  agents: {
    all: ["agents"] as const,
    status: () => ["agents", "status"] as const,
    metrics: (agentId: string) => ["agents", "metrics", agentId] as const,
  },
};
