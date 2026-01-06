/**
 * @fileoverview Canonical TanStack Query client configuration (server + client).
 */

import {
  defaultShouldDehydrateQuery,
  isServer,
  QueryClient,
} from "@tanstack/react-query";
import { shouldRetryError } from "@/lib/api/error-types";
import { keys } from "@/lib/keys";
import { cacheTimes, staleTimes } from "@/lib/query/config";

function buildQueryClient(): QueryClient {
  const client = new QueryClient({
    defaultOptions: {
      dehydrate: {
        shouldDehydrateQuery: (query) =>
          defaultShouldDehydrateQuery(query) || query.state.status === "pending",
        shouldRedactErrors: () => process.env.NODE_ENV === "production",
      },
      mutations: {
        networkMode: "online",
        retry: false,
      },
      queries: {
        ...(isServer ? {} : { gcTime: cacheTimes.medium }),
        networkMode: "online",
        refetchOnMount: true,
        refetchOnReconnect: true,
        refetchOnWindowFocus: false,
        retry: (failureCount, error) => failureCount < 2 && shouldRetryError(error),
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
        // Global fallback for queries without per-key defaults.
        staleTime: staleTimes.default,
      },
    },
  });

  const featureDefaults: ReadonlyArray<{
    gcTime: number;
    queryKey: readonly unknown[];
    staleTime: number;
  }> = [
    {
      gcTime: cacheTimes.medium,
      queryKey: keys.trips.all(),
      staleTime: staleTimes.trips,
    },
    { gcTime: cacheTimes.short, queryKey: keys.chat.all(), staleTime: staleTimes.chat },
    {
      gcTime: cacheTimes.medium,
      queryKey: keys.memory.all(),
      staleTime: staleTimes.memory,
    },
    {
      gcTime: cacheTimes.medium,
      queryKey: keys.budget.all(),
      staleTime: staleTimes.budget,
    },
    {
      gcTime: cacheTimes.long,
      queryKey: keys.currency.all(),
      staleTime: staleTimes.currency,
    },
  ];

  for (const { gcTime, queryKey, staleTime } of featureDefaults) {
    client.setQueryDefaults(queryKey, {
      ...(isServer ? {} : { gcTime }),
      staleTime,
    });
  }

  return client;
}

/**
 * Create a brand-new QueryClient instance with app defaults.
 *
 * Use for server-side prefetch/dehydration or in rare cases where a fresh client
 * is explicitly required.
 */
export function createQueryClient(): QueryClient {
  return buildQueryClient();
}

let browserQueryClient: QueryClient | undefined;

/**
 * Returns the correct QueryClient for the current environment.
 *
 * - Server: always a new QueryClient
 * - Client: a singleton QueryClient
 */
export function getQueryClient(): QueryClient {
  if (isServer) {
    return buildQueryClient();
  }

  if (!browserQueryClient) {
    browserQueryClient = buildQueryClient();
  }

  return browserQueryClient;
}
