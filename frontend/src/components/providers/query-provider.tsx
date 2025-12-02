/**
 * @fileoverview TanStack Query provider with OTEL-backed telemetry.
 * Refer to docs/development/observability.md for tracing and alerting standards.
 */

"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { type ReactNode, useState } from "react";

/**
 * Create a new QueryClient with default options.
 *
 * @returns QueryClient instance with default options.
 */
function CreateQueryClient() {
  return new QueryClient({
    defaultOptions: {
      mutations: {
        networkMode: "online",
        retry: (failureCount, error) => {
          // Don't retry mutations for 4xx errors
          if (error instanceof Error && "status" in error) {
            const status = (error as Error & { status: number }).status;
            if (status >= 400 && status < 500) return false;
          }
          // Retry once for 5xx errors or network issues
          return failureCount < 1;
        },
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
      },
      queries: {
        gcTime: 10 * 60 * 1000, // 10 minutes - cache retention
        // Enable network mode for proper error handling
        networkMode: "online",
        refetchOnMount: true,
        refetchOnReconnect: true,
        refetchOnWindowFocus: false,
        retry: (failureCount, error) => {
          // Don't retry for 4xx errors (client errors)
          if (error instanceof Error && "status" in error) {
            const status = (error as Error & { status: number }).status;
            if (status >= 400 && status < 500) return false;
          }
          // Retry up to 2 times for other errors
          return failureCount < 2;
        },
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
        staleTime: 5 * 60 * 1000, // 5 minutes - data stays fresh
      },
    },
  });
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
