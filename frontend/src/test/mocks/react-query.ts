/**
 * @fileoverview React Query mocks for component tests.
 * Use this in tests that need React Query functionality.
 * Prefer real QueryClient with test factory when possible.
 */

import type React from "react";
import { vi } from "vitest";

/**
 * Sets up React Query mocks for a test file.
 * Call this at the top level of test files that need React Query.
 *
 * @example
 * ```ts
 * import { setupReactQueryMocks } from "@/test/mocks/react-query";
 * setupReactQueryMocks();
 * ```
 */
export function setupReactQueryMocks() {
  vi.mock("@tanstack/react-query", () => {
    class QueryClientMock {
      clear = vi.fn();
      invalidateQueries = vi.fn();
      refetchQueries = vi.fn();
      setQueryData = vi.fn();
    }

    return {
      QueryClient: QueryClientMock,
      QueryClientProvider: ({ children }: { children: React.ReactNode }) => children,
      useMutation: vi.fn(() => ({
        data: { status: "success" },
        error: null,
        isError: false,
        isIdle: false,
        isLoading: false,
        isSuccess: true,
        mutate: vi.fn((data) => ({ data: { input: data, status: "success" } })),
        mutateAsync: vi.fn((data) =>
          Promise.resolve({ input: data, status: "success" })
        ),
        reset: vi.fn(),
      })),
      useQuery: vi.fn(() => ({
        data: { mockData: true },
        error: null,
        isError: false,
        isLoading: false,
        isSuccess: true,
        refetch: vi.fn(),
      })),
      useQueryClient: vi.fn(() => ({
        clear: vi.fn(),
        invalidateQueries: vi.fn(),
        refetchQueries: vi.fn(),
        setQueryData: vi.fn(),
      })),
    };
  });
}

/**
 * Creates a test QueryClient factory for tests that need real React Query behavior.
 * Prefer this over mocks when testing query logic.
 *
 * @example
 * ```ts
 * import { createTestQueryClient } from "@/test/mocks/react-query";
 * const queryClient = createTestQueryClient();
 * ```
 */
export function createTestQueryClient() {
  // Import real QueryClient for tests that need actual behavior
  const { QueryClient } = require("@tanstack/react-query");
  return new QueryClient({
    defaultOptions: {
      mutations: {
        retry: false,
      },
      queries: {
        gcTime: 0,
        retry: false,
      },
    },
  });
}
