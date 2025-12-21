/**
 * @fileoverview Lightweight typed mocks for TanStack Query primitives used in tests.
 */

import { QueryClient as TanStackQueryClient } from "@tanstack/react-query";

/**
 * Create a test QueryClient with retries disabled and zero cache persistence.
 * @returns QueryClient configured for deterministic unit tests.
 */
export const createMockQueryClient = (): TanStackQueryClient =>
  new TanStackQueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { gcTime: 0, retry: false, staleTime: 0 },
    },
  });
