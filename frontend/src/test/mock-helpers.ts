import type { SupabaseClient } from "@supabase/supabase-js";
import type { UseQueryResult } from "@tanstack/react-query";
/**
 * Comprehensive mock helpers for TypeScript compliance
 */
import { type Mock, vi } from "vitest";

// Complete Supabase Query Builder Mock
export const createCompleteQueryBuilder = (
  mockData: any = null,
  mockError: any = null
) => ({
  select: vi.fn().mockReturnThis(),
  insert: vi.fn().mockReturnThis(),
  update: vi.fn().mockReturnThis(),
  delete: vi.fn().mockReturnThis(),
  eq: vi.fn().mockReturnThis(),
  order: vi.fn().mockReturnThis(),
  range: vi.fn().mockReturnThis(),
  single: vi.fn().mockResolvedValue({ data: mockData, error: mockError }),
  maybeSingle: vi.fn().mockResolvedValue({ data: mockData, error: mockError }),
});

// Complete Supabase Client Mock
export const createMockSupabaseClient = (): Partial<SupabaseClient> => ({
  auth: {
    getSession: vi.fn().mockResolvedValue({ data: { session: null }, error: null }),
    onAuthStateChange: vi.fn().mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } },
    }),
    signUp: vi.fn().mockResolvedValue({ data: null, error: null }),
    signInWithPassword: vi.fn().mockResolvedValue({ data: null, error: null }),
    signOut: vi.fn().mockResolvedValue({ error: null }),
    resetPasswordForEmail: vi.fn().mockResolvedValue({ data: null, error: null }),
    updateUser: vi.fn().mockResolvedValue({ data: null, error: null }),
  } as any,
  from: vi.fn().mockReturnValue(createCompleteQueryBuilder()),
  channel: vi.fn().mockReturnValue({
    on: vi.fn().mockReturnThis(),
    subscribe: vi.fn().mockReturnValue({
      unsubscribe: vi.fn(),
    }),
  }),
  removeChannel: vi.fn(),
});

// Complete UseQueryResult Mock
export const createMockUseQueryResult = <T, E = Error>(
  data: T | null = null,
  error: E | null = null,
  isLoading = false,
  isError = false
): UseQueryResult<T, E> =>
  ({
    data,
    error,
    isLoading,
    isError,
    isSuccess: !isLoading && !isError && data !== null,
    isPending: isLoading,
    isFetching: false,
    isFetched: !isLoading,
    isFetchedAfterMount: !isLoading,
    isRefetching: false,
    isLoadingError: false,
    isRefetchError: false,
    isPlaceholderData: false,
    isPaused: false,
    isStale: false,
    dataUpdatedAt: Date.now(),
    errorUpdatedAt: error ? Date.now() : 0,
    failureCount: error ? 1 : 0,
    failureReason: error,
    errorUpdateCount: error ? 1 : 0,
    status: isLoading ? "pending" : isError ? "error" : "success",
    fetchStatus: "idle",
    refetch: vi.fn().mockResolvedValue({ data, error }),
    isInitialLoading: isLoading,
    promise: Promise.resolve({ data, error } as any),
  }) as UseQueryResult<T, E>;

// Import actual ApiError class from client
export { ApiError } from "@/lib/api/client";

// Complete auth state change mock
export const createMockAuthStateChange = () =>
  vi.fn().mockImplementation((callback: (event: string, session: any) => void) => ({
    data: { subscription: { unsubscribe: vi.fn() } },
  }));

// Complete table builder mock that returns complete query builder
export const createMockTableBuilder = (
  mockResponse: any = { data: null, error: null }
) =>
  vi
    .fn()
    .mockImplementation(() =>
      createCompleteQueryBuilder(mockResponse.data, mockResponse.error)
    );

// For functions that need table-specific logic
export const createMockTableBuilderWithTable = (
  mockResponse: any = { data: null, error: null }
) =>
  vi
    .fn()
    .mockImplementation((table: string) =>
      createCompleteQueryBuilder(mockResponse.data, mockResponse.error)
    );
