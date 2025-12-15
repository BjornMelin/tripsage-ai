/**
 * @fileoverview TanStack Query provider with OTEL-backed telemetry.
 * Refer to docs/development/observability.md for tracing and alerting standards.
 */

"use client";

import { QueryClient, QueryClientProvider, type QueryKey } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { type ReactNode, useState } from "react";
import { shouldRetryError } from "@/lib/api/error-types";
import { cacheTimes, staleTimes } from "@/lib/query/config";

type QueryDefault = {
  gcTime: number;
  queryKey: QueryKey;
  staleTime: number;
};

/**
 * Create a new QueryClient with default options.
 *
 * @returns QueryClient instance with default options.
 */
function CreateQueryClient() {
  const client = new QueryClient({
    defaultOptions: {
      mutations: {
        networkMode: "online",
        retry: false,
      },
      queries: {
        gcTime: cacheTimes.medium,
        networkMode: "online",
        refetchOnMount: true,
        refetchOnReconnect: true,
        refetchOnWindowFocus: false,
        retry: (failureCount, error) => failureCount < 2 && shouldRetryError(error),
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
        // Global fallback for queries without per-key staleTime defaults.
        staleTime: staleTimes.default,
      },
    },
  });

  const queryDefaults: readonly QueryDefault[] = [
    { gcTime: cacheTimes.medium, queryKey: ["trips"], staleTime: staleTimes.trips },
    { gcTime: cacheTimes.short, queryKey: ["chat"], staleTime: staleTimes.chat },
    { gcTime: cacheTimes.medium, queryKey: ["memory"], staleTime: staleTimes.memory },
    { gcTime: cacheTimes.medium, queryKey: ["budget"], staleTime: staleTimes.budget },
    { gcTime: cacheTimes.long, queryKey: ["currency"], staleTime: staleTimes.currency },
  ];

  for (const { gcTime, queryKey, staleTime } of queryDefaults) {
    client.setQueryDefaults(queryKey, { gcTime, staleTime });
  }

  return client;
}

/**
 * TanStack Query provider component.
 *
 * @param children - React children to wrap with QueryProvider.
 * @returns QueryProvider component wrapping the children.
 */
export function TanStackQueryProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(CreateQueryClient);

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools
        initialIsOpen={false}
        position="bottom"
        buttonPosition="bottom-right"
      />
    </QueryClientProvider>
  );
}
