/**
 * @fileoverview Generic mock helpers for React Query and other testing utilities.
 */

import type { UseInfiniteQueryResult, UseQueryResult } from "@tanstack/react-query";
import { vi } from "vitest";

/**
 * Creates a mock TanStack Query result for testing React Query hooks.
 * Provides realistic query state with customizable data, error, and loading states.
 *
 * @param data Optional data to return from the query
 * @param error Optional error to return from the query
 * @param isLoading Whether the query is in loading state
 * @param isError Whether the query is in error state
 * @returns A complete UseQueryResult mock with all required properties
 */
export const createMockUseQueryResult = <T, E = Error>(
  data: T | null = null,
  error: E | null = null,
  isLoading = false,
  isError = false
): UseQueryResult<T, E> => {
  const refetch = vi.fn();
  const result = {
    data: (data ?? undefined) as T | undefined,
    dataUpdatedAt: Date.now(),
    error: (error ?? null) as E | null,
    errorUpdateCount: error ? 1 : 0,
    errorUpdatedAt: error ? Date.now() : 0,
    failureCount: error ? 1 : 0,
    failureReason: error ?? null,
    fetchStatus: "idle",
    isEnabled: !isLoading,
    isError,
    isFetched: !isLoading,
    isFetchedAfterMount: !isLoading,
    isFetching: false,
    isInitialLoading: isLoading,
    isLoading,
    isLoadingError: isError && isLoading,
    isPaused: false,
    isPending: isLoading,
    isPlaceholderData: false,
    isRefetchError: false,
    isRefetching: false,
    isStale: false,
    isSuccess: !isLoading && !isError && data !== null,
    promise: Promise.resolve(data as T),
    refetch,
    status: isLoading ? "pending" : isError ? "error" : "success",
  } as UseQueryResult<T, E>;

  refetch.mockImplementation(async () => result);

  return result;
};

/**
 * Creates a mock TanStack Query infinite query result for testing infinite scroll hooks.
 * Provides default values for all infinite query properties with optional overrides.
 *
 * @param overrides Optional properties to override in the mock result
 * @returns A complete UseInfiniteQueryResult mock with realistic default values
 */
export const createMockInfiniteQueryResult = <T, E = Error>(
  overrides: Partial<UseInfiniteQueryResult<T, E>> = {}
): UseInfiniteQueryResult<T, E> => {
  const result = {
    data: undefined,
    error: null,
    fetchNextPage: vi.fn(),
    fetchPreviousPage: vi.fn(),
    fetchStatus: "idle",
    hasNextPage: false,
    hasPreviousPage: false,
    isError: false,
    isFetching: false,
    isFetchingNextPage: false,
    isFetchingPreviousPage: false,
    isLoading: false,
    isPending: false,
    isSuccess: true,
    refetch: vi.fn(),
    status: "success",
    ...overrides,
  } as UseInfiniteQueryResult<T, E>;

  return result;
};
