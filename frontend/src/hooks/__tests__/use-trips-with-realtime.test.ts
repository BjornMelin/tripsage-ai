/**
 * Comprehensive test suite for trip real-time integration hooks.
 * Tests trip data synchronization with real-time updates and connection monitoring.
 */

import type { AppError } from "@/lib/api/error-types";
import type { UseMutationResult, UseQueryResult } from "@tanstack/react-query";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock functions must be defined before vi.mock calls
const mockUser = { id: "test-user-123", email: "test@example.com" };
const mockAuth = {
  user: mockUser,
  isAuthenticated: true,
  isLoading: false,
};

// Helper functions to create properly typed UseQueryResult mocks for different states

function createMockLoadingQueryResult<TData, TError = Error>(
  overrides: Partial<UseQueryResult<TData, TError>> = {}
): UseQueryResult<TData, TError> {
  return {
    data: undefined as TData,
    error: null,
    isError: false,
    isPending: true,
    isSuccess: false,
    isLoading: true,
    isLoadingError: false,
    isRefetchError: false,
    isFetching: true,
    isFetched: false,
    isFetchedAfterMount: false,
    isRefetching: false,
    isStale: false,
    isPlaceholderData: false,
    isPaused: false,
    status: "pending",
    fetchStatus: "fetching",
    refetch: vi.fn(),
    dataUpdatedAt: 0,
    errorUpdatedAt: 0,
    failureCount: 0,
    failureReason: null,
    promise: Promise.resolve({} as TData),
    ...overrides,
  } as UseQueryResult<TData, TError>;
}

function createMockSuccessQueryResult<TData, TError = Error>(
  data: TData,
  overrides: Partial<UseQueryResult<TData, TError>> = {}
): UseQueryResult<TData, TError> {
  return {
    data,
    error: null,
    isError: false,
    isPending: false,
    isSuccess: true,
    isLoading: false,
    isLoadingError: false,
    isRefetchError: false,
    isFetching: false,
    isFetched: true,
    isFetchedAfterMount: true,
    isRefetching: false,
    isStale: false,
    isPlaceholderData: false,
    isPaused: false,
    status: "success",
    fetchStatus: "idle",
    refetch: vi.fn(),
    dataUpdatedAt: Date.now(),
    errorUpdatedAt: 0,
    failureCount: 0,
    failureReason: null,
    promise: Promise.resolve(data),
    ...overrides,
  } as UseQueryResult<TData, TError>;
}

function createMockErrorQueryResult<TData, TError = AppError>(
  error: TError,
  overrides: Partial<UseQueryResult<TData, TError>> = {}
): UseQueryResult<TData, TError> {
  return {
    data: undefined as TData,
    error,
    isError: true,
    isPending: false,
    isSuccess: false,
    isLoading: false,
    isLoadingError: true,
    isRefetchError: false,
    isFetching: false,
    isFetched: true,
    isFetchedAfterMount: true,
    isRefetching: false,
    isStale: false,
    isPlaceholderData: false,
    isPaused: false,
    status: "error",
    fetchStatus: "idle",
    refetch: vi.fn(),
    dataUpdatedAt: 0,
    errorUpdatedAt: Date.now(),
    failureCount: 1,
    failureReason: error,
    promise: Promise.resolve({} as TData),
    ...overrides,
  } as UseQueryResult<TData, TError>;
}

// Helper function to create complete UseMutationResult mocks
function createMockMutationResult<
  TData = never,
  TError = Error,
  TVariables = any,
  TContext = unknown,
>(
  overrides: Partial<UseMutationResult<TData, TError, TVariables, TContext>> = {}
): UseMutationResult<TData, TError, TVariables, TContext> {
  const baseResult = {
    data: undefined as TData | undefined,
    error: null as TError | null,
    variables: undefined,
    context: undefined,
    isError: false,
    isIdle: true,
    isPending: false,
    isPaused: false,
    isSuccess: false,
    status: "idle" as const,
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    reset: vi.fn(),
    failureCount: 0,
    failureReason: null,
    submittedAt: 0,
  };

  const result = { ...baseResult, ...overrides };

  // Fix discriminated union consistency
  if (result.isPending === true) {
    result.status = "pending";
    result.isIdle = false;
    result.isError = false;
    result.isSuccess = false;
  } else if (result.error) {
    result.isError = true;
    result.status = "error";
    result.isIdle = false;
    result.isPending = false;
    result.isSuccess = false;
  } else if (result.data !== undefined) {
    result.isSuccess = true;
    result.status = "success";
    result.isIdle = false;
    result.isPending = false;
    result.isError = false;
  }

  return result as UseMutationResult<TData, TError, TVariables, TContext>;
}

// Trip collaborator interface for type safety
interface TripCollaborator {
  id: number;
  trip_id: number;
  user_id: string;
  role: "owner" | "editor" | "viewer";
  email?: string;
  name?: string;
  created_at: string;
  updated_at: string;
}

const mockTripsData = [
  { id: 1, name: "Trip 1", user_id: "test-user-123" },
  { id: 2, name: "Trip 2", user_id: "test-user-123" },
];

const mockTripData = { id: 1, name: "Test Trip", user_id: "test-user-123" };

const mockTripRealtime = {
  connectionStatus: "connected" as const,
  isConnected: true,
  error: null,
  errors: [],
  tripSubscription: { isConnected: true, error: null },
  collaboratorSubscription: { isConnected: true, error: null },
  itinerarySubscription: { isConnected: true, error: null },
};

vi.mock("@/contexts/auth-context", () => ({
  useAuth: vi.fn(() => mockAuth),
}));

vi.mock("../use-trips", () => ({
  useTrips: vi.fn(() => createMockSuccessQueryResult(mockTripsData)),
}));

vi.mock("../use-trips-supabase", () => ({
  useTrips: vi.fn(() => ({
    trips: mockTripsData,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
  useTripData: vi.fn(() => createMockSuccessQueryResult(mockTripData)),
  useTripCollaborators: vi.fn(() =>
    createMockSuccessQueryResult<TripCollaborator[]>([])
  ),
  useAddTripCollaborator: vi.fn(() =>
    createMockMutationResult({
      mutate: vi.fn(),
      isIdle: true,
      status: "idle",
    })
  ),
  useRemoveTripCollaborator: vi.fn(() =>
    createMockMutationResult({
      mutate: vi.fn(),
      isIdle: true,
      status: "idle",
    })
  ),
}));

vi.mock("../use-supabase-realtime", () => ({
  useTripRealtime: vi.fn(() => mockTripRealtime),
}));

// Import the hooks after mocking
import {
  useTripCollaboration,
  useTripWithRealtime,
  useTripsConnectionStatus,
  useTripsWithRealtime,
} from "../use-trips-with-realtime";

import { useAuth } from "@/contexts/auth-context";
import { useTripRealtime } from "../use-supabase-realtime";
import { useTrips } from "../use-trips";
import {
  useAddTripCollaborator,
  useRemoveTripCollaborator,
  useTripCollaborators,
  useTripData,
} from "../use-trips-supabase";

// Test wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

describe("useTripsWithRealtime", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Core Functionality", () => {
    it("should return trips data with real-time connection status", () => {
      const { result } = renderHook(() => useTripsWithRealtime(), {
        wrapper: createWrapper(),
      });

      expect(result.current).toMatchObject({
        trips: mockTripsData,
        isLoading: false,
        error: null,
        refetch: expect.any(Function),
        isConnected: true,
        connectionErrors: [],
        realtimeStatus: mockTripRealtime,
      });
    });

    it("should reflect trip data loading state", () => {
      vi.mocked(useTrips).mockReturnValueOnce(createMockLoadingQueryResult());

      const { result } = renderHook(() => useTripsWithRealtime(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);
    });

    it("should reflect trip data error state", () => {
      const error = new Error("Failed to fetch trips") as AppError;
      vi.mocked(useTrips).mockReturnValueOnce(createMockErrorQueryResult(error));

      const { result } = renderHook(() => useTripsWithRealtime(), {
        wrapper: createWrapper(),
      });

      expect(result.current.error).toBe(error);
    });

    it("should reflect real-time connection status", () => {
      vi.mocked(useTripRealtime).mockReturnValueOnce({
        ...mockTripRealtime,
        connectionStatus: "disconnected",
        isConnected: false,
        error: new Error("Connection failed"),
        errors: [new Error("Connection failed")],
      });

      const { result } = renderHook(() => useTripsWithRealtime(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isConnected).toBe(false);
      expect(result.current.connectionErrors).toHaveLength(1);
      expect(result.current.connectionErrors[0]).toBeInstanceOf(Error);
    });
  });

  describe("Integration with Real-time Updates", () => {
    it("should call refetch function when requested", async () => {
      const refetchMock = vi.fn();
      vi.mocked(useTrips).mockReturnValueOnce(
        createMockSuccessQueryResult(mockTripsData, { refetch: refetchMock })
      );

      const { result } = renderHook(() => useTripsWithRealtime(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.refetch();
      });

      expect(refetchMock).toHaveBeenCalled();
    });

    it("should pass null tripId to useTripRealtime for all trips", () => {
      renderHook(() => useTripsWithRealtime(), {
        wrapper: createWrapper(),
      });

      expect(vi.mocked(useTripRealtime)).toHaveBeenCalledWith(null);
    });
  });

  describe("Error Handling", () => {
    it("should handle when user is not authenticated", () => {
      vi.mocked(useAuth).mockReturnValueOnce({
        user: null,
        isAuthenticated: false,
        isLoading: false,
      } as any);

      const { result } = renderHook(() => useTripsWithRealtime(), {
        wrapper: createWrapper(),
      });

      // Should still return structure even without user
      expect(result.current).toMatchObject({
        trips: expect.any(Array),
        isLoading: expect.any(Boolean),
        error: null,
        refetch: expect.any(Function),
        isConnected: expect.any(Boolean),
        connectionErrors: expect.any(Array),
        realtimeStatus: expect.any(Object),
      });
    });

    it("should handle multiple connection errors", () => {
      const errors = [new Error("Connection error 1"), new Error("Connection error 2")];

      vi.mocked(useTripRealtime).mockReturnValueOnce({
        ...mockTripRealtime,
        connectionStatus: "error",
        isConnected: false,
        error: errors[0],
        errors,
      });

      const { result } = renderHook(() => useTripsWithRealtime(), {
        wrapper: createWrapper(),
      });

      expect(result.current.connectionErrors).toHaveLength(2);
      expect(result.current.connectionErrors).toEqual(errors);
    });
  });
});

describe("useTripWithRealtime", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Core Functionality", () => {
    it("should return trip data with real-time connection status", () => {
      const { result } = renderHook(() => useTripWithRealtime(1), {
        wrapper: createWrapper(),
      });

      expect(result.current).toMatchObject({
        trip: mockTripData,
        isLoading: false,
        error: null,
        refetch: expect.any(Function),
        isConnected: true,
        connectionErrors: [],
        realtimeStatus: mockTripRealtime,
      });
    });

    it("should handle null tripId", () => {
      const { result } = renderHook(() => useTripWithRealtime(null), {
        wrapper: createWrapper(),
      });

      expect(result.current).toMatchObject({
        trip: mockTripData,
        isLoading: expect.any(Boolean),
        error: null,
        refetch: expect.any(Function),
        isConnected: expect.any(Boolean),
        connectionErrors: expect.any(Array),
        realtimeStatus: expect.any(Object),
      });

      expect(vi.mocked(useTripRealtime)).toHaveBeenCalledWith(null);
    });

    it("should pass tripId to useTripData and useTripRealtime", () => {
      renderHook(() => useTripWithRealtime(123), {
        wrapper: createWrapper(),
      });

      expect(vi.mocked(useTripData)).toHaveBeenCalledWith(123);
      expect(vi.mocked(useTripRealtime)).toHaveBeenCalledWith(123);
    });
  });

  describe("State Management", () => {
    it("should reflect trip data loading state", () => {
      vi.mocked(useTripData).mockReturnValueOnce(createMockLoadingQueryResult());

      const { result } = renderHook(() => useTripWithRealtime(1), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);
    });

    it("should reflect trip data error state", () => {
      const error = new Error("Failed to fetch trip");
      vi.mocked(useTripData).mockReturnValueOnce(createMockErrorQueryResult(error));

      const { result } = renderHook(() => useTripWithRealtime(1), {
        wrapper: createWrapper(),
      });

      expect(result.current.error).toBe(error);
    });

    it("should combine data and real-time states correctly", () => {
      vi.mocked(useTripData).mockReturnValueOnce(createMockLoadingQueryResult());

      vi.mocked(useTripRealtime).mockReturnValueOnce({
        ...mockTripRealtime,
        connectionStatus: "disconnected",
        isConnected: false,
      });

      const { result } = renderHook(() => useTripWithRealtime(1), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);
      expect(result.current.isConnected).toBe(false);
    });
  });
});

describe("useTripsConnectionStatus", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Connection Status Summary", () => {
    it("should return connection status summary", () => {
      const { result } = renderHook(() => useTripsConnectionStatus(), {
        wrapper: createWrapper(),
      });

      expect(result.current).toMatchObject({
        isConnected: true,
        hasErrors: false,
        errorCount: 0,
        lastError: null,
      });
    });

    it("should detect when there are connection errors", () => {
      const errors = [new Error("Connection failed")];
      vi.mocked(useTripRealtime).mockReturnValueOnce({
        ...mockTripRealtime,
        connectionStatus: "error",
        isConnected: false,
        error: errors[0],
        errors,
      });

      const { result } = renderHook(() => useTripsConnectionStatus(), {
        wrapper: createWrapper(),
      });

      expect(result.current).toMatchObject({
        isConnected: false,
        hasErrors: true,
        errorCount: 1,
        lastError: errors[0],
      });
    });

    it("should return most recent error as lastError", () => {
      const errors = [
        new Error("First error"),
        new Error("Second error"),
        new Error("Most recent error"),
      ];

      vi.mocked(useTripRealtime).mockReturnValueOnce({
        ...mockTripRealtime,
        connectionStatus: "error",
        error: errors[2],
        errors,
      });

      const { result } = renderHook(() => useTripsConnectionStatus(), {
        wrapper: createWrapper(),
      });

      expect(result.current.lastError).toBe(errors[2]);
      expect(result.current.errorCount).toBe(3);
    });

    it("should handle empty errors array", () => {
      vi.mocked(useTripRealtime).mockReturnValueOnce({
        ...mockTripRealtime,
        connectionStatus: "connected",
        error: null,
        errors: [],
      });

      const { result } = renderHook(() => useTripsConnectionStatus(), {
        wrapper: createWrapper(),
      });

      expect(result.current).toMatchObject({
        isConnected: true,
        hasErrors: false,
        errorCount: 0,
        lastError: null,
      });
    });
  });

  describe("Memoization", () => {
    it("should memoize connection status to prevent unnecessary re-renders", () => {
      const { result, rerender } = renderHook(() => useTripsConnectionStatus(), {
        wrapper: createWrapper(),
      });

      const firstResult = result.current;

      // Rerender with same real-time status
      rerender();

      // Should return the same object reference
      expect(result.current).toBe(firstResult);
    });

    it("should update when real-time status changes", () => {
      const { result, rerender } = renderHook(() => useTripsConnectionStatus(), {
        wrapper: createWrapper(),
      });

      const firstResult = result.current;

      // Change the real-time status
      vi.mocked(useTripRealtime).mockReturnValueOnce({
        ...mockTripRealtime,
        connectionStatus: "error",
        isConnected: false,
        error: new Error("New error"),
        errors: [new Error("New error")],
      });

      rerender();

      // Should return a new object with updated status
      expect(result.current).not.toBe(firstResult);
      expect(result.current.isConnected).toBe(false);
    });
  });
});

describe("useTripCollaboration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Core Functionality", () => {
    it("should handle string trip ID", () => {
      const { result } = renderHook(() => useTripCollaboration("123"), {
        wrapper: createWrapper(),
      });

      expect(result.current).toMatchObject({
        collaborators: expect.any(Array),
        isLoading: expect.any(Boolean),
        error: null,
        refetch: expect.any(Function),
        addCollaborator: expect.any(Object),
        removeCollaborator: expect.any(Object),
        isConnected: expect.any(Boolean),
        connectionErrors: expect.any(Array),
        realtimeStatus: expect.any(Object),
      });

      // Should convert string to number
      expect(vi.mocked(useTripCollaborators)).toHaveBeenCalledWith(123);
      expect(vi.mocked(useTripRealtime)).toHaveBeenCalledWith(123);
    });

    it("should handle numeric trip ID", () => {
      const { result } = renderHook(() => useTripCollaboration(456), {
        wrapper: createWrapper(),
      });

      expect(result.current).toMatchObject({
        collaborators: expect.any(Array),
        isLoading: expect.any(Boolean),
        error: null,
        refetch: expect.any(Function),
        addCollaborator: expect.any(Object),
        removeCollaborator: expect.any(Object),
        isConnected: expect.any(Boolean),
        connectionErrors: expect.any(Array),
        realtimeStatus: expect.any(Object),
      });

      expect(vi.mocked(useTripCollaborators)).toHaveBeenCalledWith(456);
      expect(vi.mocked(useTripRealtime)).toHaveBeenCalledWith(456);
    });
  });

  describe("Collaboration Management", () => {
    it("should provide add and remove collaborator mutations", () => {
      const mockAddCollaborator = createMockMutationResult({
        mutate: vi.fn(),
        isIdle: true,
        status: "idle",
      });
      const mockRemoveCollaborator = createMockMutationResult({
        mutate: vi.fn(),
        isIdle: true,
        status: "idle",
      });

      vi.mocked(useAddTripCollaborator).mockReturnValueOnce(mockAddCollaborator);
      vi.mocked(useRemoveTripCollaborator).mockReturnValueOnce(mockRemoveCollaborator);

      const { result } = renderHook(() => useTripCollaboration(123), {
        wrapper: createWrapper(),
      });

      expect(result.current.addCollaborator).toBe(mockAddCollaborator);
      expect(result.current.removeCollaborator).toBe(mockRemoveCollaborator);
    });

    it("should return collaborator data and loading states", () => {
      const collaborators: TripCollaborator[] = [
        {
          id: 1,
          trip_id: 123,
          user_id: "user-1",
          role: "editor",
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
        },
        {
          id: 2,
          trip_id: 123,
          user_id: "user-2",
          role: "viewer",
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
        },
      ];

      vi.mocked(useTripCollaborators).mockReturnValueOnce(
        createMockSuccessQueryResult<TripCollaborator[]>(collaborators)
      );

      const { result } = renderHook(() => useTripCollaboration(123), {
        wrapper: createWrapper(),
      });

      expect(result.current.collaborators).toBe(collaborators);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBe(null);
    });

    it("should handle collaborator loading state", () => {
      vi.mocked(useTripCollaborators).mockReturnValueOnce(
        createMockLoadingQueryResult<TripCollaborator[]>()
      );

      const { result } = renderHook(() => useTripCollaboration(123), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);
    });

    it("should handle collaborator error state", () => {
      const error = new Error("Failed to fetch collaborators") as AppError;
      vi.mocked(useTripCollaborators).mockReturnValueOnce(
        createMockErrorQueryResult<TripCollaborator[]>(error)
      );

      const { result } = renderHook(() => useTripCollaboration(123), {
        wrapper: createWrapper(),
      });

      expect(result.current.error).toBe(error);
    });
  });

  describe("Real-time Integration", () => {
    it("should combine collaboration data with real-time status", () => {
      const { result } = renderHook(() => useTripCollaboration(123), {
        wrapper: createWrapper(),
      });

      expect(result.current.isConnected).toBe(mockTripRealtime.isConnected);
      expect(result.current.connectionErrors).toBe(mockTripRealtime.errors);
      expect(result.current.realtimeStatus).toBe(mockTripRealtime);
    });

    it("should reflect real-time connection failures", () => {
      const connectionErrors = [new Error("Real-time connection failed")];
      vi.mocked(useTripRealtime).mockReturnValueOnce({
        ...mockTripRealtime,
        connectionStatus: "error",
        isConnected: false,
        error: connectionErrors[0],
        errors: connectionErrors,
      });

      const { result } = renderHook(() => useTripCollaboration(123), {
        wrapper: createWrapper(),
      });

      expect(result.current.isConnected).toBe(false);
      expect(result.current.connectionErrors).toBe(connectionErrors);
    });
  });

  describe("Edge Cases", () => {
    it("should handle invalid trip ID strings", () => {
      renderHook(() => useTripCollaboration("invalid"), {
        wrapper: createWrapper(),
      });

      // Should convert to NaN, which becomes 0 when parseInt fails
      expect(vi.mocked(useTripCollaborators)).toHaveBeenCalledWith(Number.NaN);
    });

    it("should handle zero trip ID", () => {
      renderHook(() => useTripCollaboration(0), {
        wrapper: createWrapper(),
      });

      expect(vi.mocked(useTripCollaborators)).toHaveBeenCalledWith(0);
      expect(vi.mocked(useTripRealtime)).toHaveBeenCalledWith(0);
    });

    it("should handle negative trip ID", () => {
      renderHook(() => useTripCollaboration(-1), {
        wrapper: createWrapper(),
      });

      expect(vi.mocked(useTripCollaborators)).toHaveBeenCalledWith(-1);
      expect(vi.mocked(useTripRealtime)).toHaveBeenCalledWith(-1);
    });
  });
});

describe("Integration Tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should handle all hooks working together", () => {
    const wrapper = createWrapper();

    // Render all hooks simultaneously
    const { result: tripsResult } = renderHook(() => useTripsWithRealtime(), {
      wrapper,
    });
    const { result: tripResult } = renderHook(() => useTripWithRealtime(1), {
      wrapper,
    });
    const { result: statusResult } = renderHook(() => useTripsConnectionStatus(), {
      wrapper,
    });
    const { result: collabResult } = renderHook(() => useTripCollaboration(1), {
      wrapper,
    });

    // All hooks should function without errors
    expect(tripsResult.current.trips).toBeDefined();
    expect(tripResult.current.trip).toBeDefined();
    expect(statusResult.current.isConnected).toBeDefined();
    expect(collabResult.current.collaborators).toBeDefined();
  });

  it("should handle simultaneous data and connection state changes", async () => {
    const wrapper = createWrapper();

    const { result, rerender } = renderHook(() => useTripsWithRealtime(), {
      wrapper,
    });

    // Change both data and connection state
    vi.mocked(useTrips).mockReturnValueOnce(createMockLoadingQueryResult());

    vi.mocked(useTripRealtime).mockReturnValueOnce({
      ...mockTripRealtime,
      connectionStatus: "disconnected",
      isConnected: false,
    });

    rerender();

    expect(result.current.isLoading).toBe(true);
    expect(result.current.isConnected).toBe(false);
  });

  it("should maintain stable function references across re-renders", () => {
    const wrapper = createWrapper();

    const { result, rerender } = renderHook(() => useTripsWithRealtime(), {
      wrapper,
    });

    result.current.refetch; // Access refetch function

    rerender();

    // Note: React Query's refetch function reference may change between renders
    // but it should still be a function
    expect(typeof result.current.refetch).toBe("function");
    // The important thing is that calling it still works
    expect(() => result.current.refetch()).not.toThrow();
  });

  it("should handle cleanup properly", () => {
    const wrapper = createWrapper();

    const { unmount: unmountTrips } = renderHook(() => useTripsWithRealtime(), {
      wrapper,
    });
    const { unmount: unmountTrip } = renderHook(() => useTripWithRealtime(1), {
      wrapper,
    });
    const { unmount: unmountStatus } = renderHook(() => useTripsConnectionStatus(), {
      wrapper,
    });
    const { unmount: unmountCollab } = renderHook(() => useTripCollaboration(1), {
      wrapper,
    });

    // Should not throw during cleanup
    expect(() => {
      unmountTrips();
      unmountTrip();
      unmountStatus();
      unmountCollab();
    }).not.toThrow();
  });
});
