"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { type ReactNode, useState } from "react";

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5 * 60 * 1000, // 5 minutes - data stays fresh
        gcTime: 10 * 60 * 1000, // 10 minutes - cache retention
        retry: (failureCount, error) => {
          // Don't retry for 4xx errors (client errors)
          if (error instanceof Error && "status" in error) {
            const status = (error as any).status;
            if (status >= 400 && status < 500) return false;
          }
          // Retry up to 2 times for other errors
          return failureCount < 2;
        },
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
        refetchOnWindowFocus: false,
        refetchOnReconnect: true,
        refetchOnMount: true,
        // Enable network mode for proper error handling
        networkMode: "online",
      },
      mutations: {
        retry: (failureCount, error) => {
          // Don't retry mutations for 4xx errors
          if (error instanceof Error && "status" in error) {
            const status = (error as any).status;
            if (status >= 400 && status < 500) return false;
          }
          // Retry once for 5xx errors or network issues
          return failureCount < 1;
        },
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
        networkMode: "online",
      },
    },
  });
}

export function TanStackQueryProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(createQueryClient);

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
