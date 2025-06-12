/**
 * Comprehensive test suite for trip real-time integration hooks.
 * Tests trip data synchronization with real-time updates and connection monitoring.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock the auth context
const mockUser = { id: "test-user-123", email: "test@example.com" };
const mockAuth = {
  user: mockUser,
  isAuthenticated: true,
  isLoading: false,
};

vi.mock("@/contexts/auth-context", () => ({
  useAuth: vi.fn(() => mockAuth),
}));

// Mock trip data hooks
const mockTripsData = [
  { id: 1, name: "Trip 1", user_id: "test-user-123" },
  { id: 2, name: "Trip 2", user_id: "test-user-123" },
];

const mockTripData = { id: 1, name: "Test Trip", user_id: "test-user-123" };

const mockUseTrips = {
  trips: mockTripsData,
  isLoading: false,
  error: null,
  refetch: vi.fn(),
};

const mockUseTripData = {
  trip: mockTripData,
  isLoading: false,
  error: null,
  refetch: vi.fn(),
};

const mockUseTripCollaborators = {
  collaborators: [],
  isLoading: false,
  error: null,
  refetch: vi.fn(),
};

vi.mock("../use-trips-supabase", () => ({
  useTrips: vi.fn(() => mockUseTrips),
  useTripData: vi.fn(() => mockUseTripData),
  useTripCollaborators: vi.fn(() => mockUseTripCollaborators),
  useAddTripCollaborator: vi.fn(() => ({ mutate: vi.fn(), isLoading: false })),
  useRemoveTripCollaborator: vi.fn(() => ({ mutate: vi.fn(), isLoading: false })),
}));

// Mock the real-time hooks
const mockTripRealtime = {
  isConnected: true,
  errors: [],
  tripSubscription: { isConnected: true, error: null },
  collaboratorSubscription: { isConnected: true, error: null },
  itinerarySubscription: { isConnected: true, error: null },
};

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
      vi.mocked(require("../use-trips-supabase").useTrips).mockReturnValueOnce({
        ...mockUseTrips,
        isLoading: true,
      });

      const { result } = renderHook(() => useTripsWithRealtime(), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);
    });

    it("should reflect trip data error state", () => {
      const error = new Error("Failed to fetch trips");
      vi.mocked(require("../use-trips-supabase").useTrips).mockReturnValueOnce({
        ...mockUseTrips,
        error,
      });

      const { result } = renderHook(() => useTripsWithRealtime(), {
        wrapper: createWrapper(),
      });

      expect(result.current.error).toBe(error);
    });

    it("should reflect real-time connection status", () => {
      vi.mocked(require("../use-supabase-realtime").useTripRealtime).mockReturnValueOnce({
        ...mockTripRealtime,
        isConnected: false,
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
      const { result } = renderHook(() => useTripsWithRealtime(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.refetch();
      });

      expect(mockUseTrips.refetch).toHaveBeenCalled();
    });

    it("should pass null tripId to useTripRealtime for all trips", () => {
      renderHook(() => useTripsWithRealtime(), {
        wrapper: createWrapper(),
      });

      expect(require("../use-supabase-realtime").useTripRealtime).toHaveBeenCalledWith(
        null
      );
    });
  });

  describe("Error Handling", () => {
    it("should handle when user is not authenticated", () => {
      vi.mocked(require("@/contexts/auth-context").useAuth).mockReturnValueOnce({
        user: null,
        isAuthenticated: false,
        isLoading: false,
      });

      const { result } = renderHook(() => useTripsWithRealtime(), {
        wrapper: createWrapper(),
      });

      // Should still return structure even without user
      expect(result.current).toMatchObject({
        trips: expect.any(Array),
        isLoading: expect.any(Boolean),
        error: expect.anything(),
        refetch: expect.any(Function),
        isConnected: expect.any(Boolean),
        connectionErrors: expect.any(Array),
        realtimeStatus: expect.any(Object),
      });
    });

    it("should handle multiple connection errors", () => {
      const errors = [
        new Error("Connection error 1"),
        new Error("Connection error 2"),
      ];

      vi.mocked(require("../use-supabase-realtime").useTripRealtime).mockReturnValueOnce({
        ...mockTripRealtime,
        isConnected: false,
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
        trip: expect.anything(),
        isLoading: expect.any(Boolean),
        error: expect.anything(),
        refetch: expect.any(Function),
        isConnected: expect.any(Boolean),
        connectionErrors: expect.any(Array),
        realtimeStatus: expect.any(Object),
      });

      expect(require("../use-supabase-realtime").useTripRealtime).toHaveBeenCalledWith(
        null
      );
    });

    it("should pass tripId to useTripData and useTripRealtime", () => {
      renderHook(() => useTripWithRealtime(123), {
        wrapper: createWrapper(),
      });

      expect(require("../use-trips-supabase").useTripData).toHaveBeenCalledWith(123);
      expect(require("../use-supabase-realtime").useTripRealtime).toHaveBeenCalledWith(
        123
      );
    });
  });

  describe("State Management", () => {
    it("should reflect trip data loading state", () => {
      vi.mocked(require("../use-trips-supabase").useTripData).mockReturnValueOnce({
        ...mockUseTripData,
        isLoading: true,
      });

      const { result } = renderHook(() => useTripWithRealtime(1), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);
    });

    it("should reflect trip data error state", () => {
      const error = new Error("Failed to fetch trip");
      vi.mocked(require("../use-trips-supabase").useTripData).mockReturnValueOnce({
        ...mockUseTripData,
        error,
      });

      const { result } = renderHook(() => useTripWithRealtime(1), {
        wrapper: createWrapper(),
      });

      expect(result.current.error).toBe(error);
    });

    it("should combine data and real-time states correctly", () => {
      vi.mocked(require("../use-trips-supabase").useTripData).mockReturnValueOnce({
        ...mockUseTripData,
        isLoading: true,
      });

      vi.mocked(require("../use-supabase-realtime").useTripRealtime).mockReturnValueOnce({
        ...mockTripRealtime,
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
      vi.mocked(require("../use-supabase-realtime").useTripRealtime).mockReturnValueOnce({
        ...mockTripRealtime,
        isConnected: false,
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

      vi.mocked(require("../use-supabase-realtime").useTripRealtime).mockReturnValueOnce({
        ...mockTripRealtime,
        errors,
      });

      const { result } = renderHook(() => useTripsConnectionStatus(), {
        wrapper: createWrapper(),
      });

      expect(result.current.lastError).toBe(errors[2]);
      expect(result.current.errorCount).toBe(3);
    });

    it("should handle empty errors array", () => {
      vi.mocked(require("../use-supabase-realtime").useTripRealtime).mockReturnValueOnce({
        ...mockTripRealtime,
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
      vi.mocked(require("../use-supabase-realtime").useTripRealtime).mockReturnValueOnce({
        ...mockTripRealtime,
        isConnected: false,
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
        error: expect.anything(),
        refetch: expect.any(Function),
        addCollaborator: expect.any(Object),
        removeCollaborator: expect.any(Object),
        isConnected: expect.any(Boolean),
        connectionErrors: expect.any(Array),
        realtimeStatus: expect.any(Object),
      });

      // Should convert string to number
      expect(require("../use-trips-supabase").useTripCollaborators).toHaveBeenCalledWith(
        123
      );
      expect(require("../use-supabase-realtime").useTripRealtime).toHaveBeenCalledWith(
        123
      );
    });

    it("should handle numeric trip ID", () => {
      const { result } = renderHook(() => useTripCollaboration(456), {
        wrapper: createWrapper(),
      });

      expect(result.current).toMatchObject({
        collaborators: expect.any(Array),
        isLoading: expect.any(Boolean),
        error: expect.anything(),
        refetch: expect.any(Function),
        addCollaborator: expect.any(Object),
        removeCollaborator: expect.any(Object),
        isConnected: expect.any(Boolean),
        connectionErrors: expect.any(Array),
        realtimeStatus: expect.any(Object),
      });

      expect(require("../use-trips-supabase").useTripCollaborators).toHaveBeenCalledWith(
        456
      );
      expect(require("../use-supabase-realtime").useTripRealtime).toHaveBeenCalledWith(
        456
      );
    });
  });

  describe("Collaboration Management", () => {
    it("should provide add and remove collaborator mutations", () => {
      const mockAddCollaborator = { mutate: vi.fn(), isLoading: false };
      const mockRemoveCollaborator = { mutate: vi.fn(), isLoading: false };

      vi.mocked(require("../use-trips-supabase").useAddTripCollaborator).mockReturnValueOnce(
        mockAddCollaborator
      );
      vi.mocked(
        require("../use-trips-supabase").useRemoveTripCollaborator
      ).mockReturnValueOnce(mockRemoveCollaborator);

      const { result } = renderHook(() => useTripCollaboration(123), {
        wrapper: createWrapper(),
      });

      expect(result.current.addCollaborator).toBe(mockAddCollaborator);
      expect(result.current.removeCollaborator).toBe(mockRemoveCollaborator);
    });

    it("should return collaborator data and loading states", () => {
      const collaborators = [
        { id: 1, trip_id: 123, user_id: "user-1", role: "editor" },
        { id: 2, trip_id: 123, user_id: "user-2", role: "viewer" },
      ];

      vi.mocked(require("../use-trips-supabase").useTripCollaborators).mockReturnValueOnce({
        collaborators,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      const { result } = renderHook(() => useTripCollaboration(123), {
        wrapper: createWrapper(),
      });

      expect(result.current.collaborators).toBe(collaborators);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBe(null);
    });

    it("should handle collaborator loading state", () => {
      vi.mocked(require("../use-trips-supabase").useTripCollaborators).mockReturnValueOnce({
        ...mockUseTripCollaborators,
        isLoading: true,
      });

      const { result } = renderHook(() => useTripCollaboration(123), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoading).toBe(true);
    });

    it("should handle collaborator error state", () => {
      const error = new Error("Failed to fetch collaborators");
      vi.mocked(require("../use-trips-supabase").useTripCollaborators).mockReturnValueOnce({
        ...mockUseTripCollaborators,
        error,
      });

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
      vi.mocked(require("../use-supabase-realtime").useTripRealtime).mockReturnValueOnce({
        ...mockTripRealtime,
        isConnected: false,
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
      const { result } = renderHook(() => useTripCollaboration("invalid"), {
        wrapper: createWrapper(),
      });

      // Should convert to NaN, which becomes 0 when parseInt fails
      expect(require("../use-trips-supabase").useTripCollaborators).toHaveBeenCalledWith(
        Number.NaN
      );
    });

    it("should handle zero trip ID", () => {
      const { result } = renderHook(() => useTripCollaboration(0), {
        wrapper: createWrapper(),
      });

      expect(require("../use-trips-supabase").useTripCollaborators).toHaveBeenCalledWith(
        0
      );
      expect(require("../use-supabase-realtime").useTripRealtime).toHaveBeenCalledWith(
        0
      );
    });

    it("should handle negative trip ID", () => {
      const { result } = renderHook(() => useTripCollaboration(-1), {
        wrapper: createWrapper(),
      });

      expect(require("../use-trips-supabase").useTripCollaborators).toHaveBeenCalledWith(
        -1
      );
      expect(require("../use-supabase-realtime").useTripRealtime).toHaveBeenCalledWith(
        -1
      );
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
    vi.mocked(require("../use-trips-supabase").useTrips).mockReturnValueOnce({
      ...mockUseTrips,
      isLoading: true,
    });

    vi.mocked(require("../use-supabase-realtime").useTripRealtime).mockReturnValueOnce({
      ...mockTripRealtime,
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

    const initialRefetch = result.current.refetch;

    rerender();

    // Function references should remain stable
    expect(result.current.refetch).toBe(initialRefetch);
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