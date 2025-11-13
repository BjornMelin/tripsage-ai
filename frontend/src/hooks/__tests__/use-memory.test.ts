/**
 * Tests for memory hooks - frontend API integration
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import React, { type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  useAddConversationMemory,
  useMemoryContext,
  useMemoryInsights,
  useMemoryStats,
  useSearchMemories,
  useUpdatePreferences,
} from "../use-memory";

// Mock the useAuthenticatedApi hook
const MOCK_MAKE_AUTHENTICATED_REQUEST = vi.fn();
vi.mock("../use-authenticated-api", () => ({
  useAuthenticatedApi: () => ({
    isAuthenticated: true,
    makeAuthenticatedRequest: MOCK_MAKE_AUTHENTICATED_REQUEST,
  }),
}));

// Test wrapper with QueryClient
const CREATE_WRAPPER = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });

  return function TestWrapper({ children }: { children: ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
};

describe("Memory Hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MOCK_MAKE_AUTHENTICATED_REQUEST.mockClear();
  });

  describe("useMemoryContext", () => {
    it("should fetch memory context for user", async () => {
      const mockResponse = {
        memories: [
          {
            content: "User prefers luxury hotels",
            created_at: "2024-01-01T10:00:00Z",
            id: "mem-1",
            metadata: { category: "accommodation", preference: "luxury" },
            score: 0.95,
          },
        ],
        preferences: {
          accommodation: "luxury",
          budget: "high",
          destinations: ["Europe", "Asia"],
        },
        travel_patterns: {
          avg_trip_duration: 7,
          booking_lead_time: 30,
          favorite_destinations: ["Paris", "Tokyo"],
        },
      };

      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(() => useMemoryContext("user-123"), {
        wrapper: CREATE_WRAPPER(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(MOCK_MAKE_AUTHENTICATED_REQUEST).toHaveBeenCalled();
      const firstCall = MOCK_MAKE_AUTHENTICATED_REQUEST.mock.calls[0];
      expect(firstCall[0]).toBe("/api/memory/context/user-123");
      expect(result.current.data).toEqual(mockResponse);
    });

    it("should not fetch when userId is empty", () => {
      const { result } = renderHook(() => useMemoryContext(""), {
        wrapper: CREATE_WRAPPER(),
      });

      expect(MOCK_MAKE_AUTHENTICATED_REQUEST).not.toHaveBeenCalled();
      expect(result.current.data).toBeUndefined();
      // When enabled is false in react-query, the query may still show as pending initially
      // but it won't actually fetch data
      expect(result.current.isSuccess).toBe(false);
      expect(result.current.isError).toBe(false);
    });

    it("should handle API errors gracefully", async () => {
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockRejectedValueOnce(new Error("API Error"));

      const { result } = renderHook(() => useMemoryContext("user-123"), {
        wrapper: CREATE_WRAPPER(),
      });

      await waitFor(
        () => {
          expect(result.current.isError).toBe(true);
        },
        { timeout: 3000 }
      );

      expect(result.current.error).toBeInstanceOf(Error);
    });
  });

  describe("useSearchMemories", () => {
    it("should search memories with query and filters", async () => {
      const mockResults = [
        {
          content: "Looking for flights to Paris",
          metadata: { destination: "Paris", type: "search" },
          score: 0.88,
        },
        {
          content: "Booked luxury hotel in Tokyo",
          metadata: { destination: "Tokyo", type: "booking" },
          score: 0.82,
        },
      ];

      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValueOnce(mockResults);

      const { result } = renderHook(() => useSearchMemories(), {
        wrapper: CREATE_WRAPPER(),
      });

      // Since useSearchMemories returns a mutation, we need to call mutate
      const searchParams = {
        filters: {
          metadata: { category: "accommodation" },
          type: ["accommodation"],
        },
        limit: 10,
        query: "travel preferences",
        userId: "user-123",
      };

      result.current.mutate(searchParams);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(MOCK_MAKE_AUTHENTICATED_REQUEST).toHaveBeenCalledWith(
        "/api/memory/search",
        {
          body: JSON.stringify(searchParams),
          headers: { "Content-Type": "application/json" },
          method: "POST",
        }
      );
      expect(result.current.data).toEqual(mockResults);
    });

    it("should handle search without filters", async () => {
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValueOnce([]);

      const { result } = renderHook(() => useSearchMemories(), {
        wrapper: CREATE_WRAPPER(),
      });

      const searchParams = {
        limit: 20, // default limit
        query: "hotels",
        userId: "user-123",
      };

      result.current.mutate(searchParams);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(MOCK_MAKE_AUTHENTICATED_REQUEST).toHaveBeenCalledWith(
        "/api/memory/search",
        {
          body: JSON.stringify(searchParams),
          headers: { "Content-Type": "application/json" },
          method: "POST",
        }
      );
    });
  });

  describe("useAddConversationMemory", () => {
    it("should store conversation memory", async () => {
      const mockResponse = { memory_id: "mem-123", status: "success" };
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(() => useAddConversationMemory(), {
        wrapper: CREATE_WRAPPER(),
      });

      const conversationData = {
        messages: [
          {
            content: "I want to book a hotel in Paris",
            role: "user" as const,
            timestamp: "2024-01-01T10:00:00Z",
          },
          {
            content: "I can help you find hotels in Paris.",
            role: "assistant" as const,
            timestamp: "2024-01-01T10:01:00Z",
          },
        ],
        sessionId: "session-123",
        userId: "user-123",
      };

      result.current.mutate(conversationData);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(MOCK_MAKE_AUTHENTICATED_REQUEST).toHaveBeenCalledWith(
        "/api/memory/conversations",
        {
          body: JSON.stringify(conversationData),
          headers: { "Content-Type": "application/json" },
          method: "POST",
        }
      );
      expect(result.current.data).toEqual(mockResponse);
    });

    it("should handle conversation storage errors", async () => {
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockRejectedValueOnce(
        new Error("Storage failed")
      );

      const { result } = renderHook(() => useAddConversationMemory(), {
        wrapper: CREATE_WRAPPER(),
      });

      const conversationData = {
        messages: [],
        sessionId: "test",
        userId: "test",
      };

      result.current.mutate(conversationData);

      await waitFor(
        () => {
          expect(result.current.isError).toBe(true);
        },
        { timeout: 3000 }
      );

      expect(result.current.error).toBeInstanceOf(Error);
    });
  });

  describe("useUpdatePreferences", () => {
    it("should update user preferences", async () => {
      const mockResponse = { status: "success" };
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(() => useUpdatePreferences("user-123"), {
        wrapper: CREATE_WRAPPER(),
      });

      const preferencesData = {
        preferences: {
          accommodation: "luxury",
          budget: "high",
          destinations: ["Europe"],
        },
        userId: "user-123",
      };

      result.current.mutate(preferencesData);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(MOCK_MAKE_AUTHENTICATED_REQUEST).toHaveBeenCalledWith(
        "/api/memory/preferences/user-123",
        {
          body: JSON.stringify(preferencesData),
          headers: { "Content-Type": "application/json" },
          method: "POST",
        }
      );
      expect(result.current.data).toEqual(mockResponse);
    });
  });

  describe("useMemoryInsights", () => {
    it("should fetch memory insights for user", async () => {
      const mockInsights = {
        ai_recommendations: [
          "Consider luxury hotels in Kyoto for your next trip",
          "Book flights 6-8 weeks in advance for best prices",
        ],
        booking_behavior: {
          avg_lead_time: 45,
          flexible_dates: true,
          price_sensitivity: 0.6,
        },
        budget_patterns: {
          avg_flight_budget: 800,
          avg_hotel_budget: 300,
          budget_consistency: 0.85,
        },
        destination_preferences: {
          city_vs_nature: 0.7,
          climate_preference: "temperate",
          preferred_regions: ["Europe", "Asia"],
        },
        travel_personality: "luxury_traveler",
      };

      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValueOnce(mockInsights);

      const { result } = renderHook(() => useMemoryInsights("user-123"), {
        wrapper: CREATE_WRAPPER(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(MOCK_MAKE_AUTHENTICATED_REQUEST).toHaveBeenCalled();
      {
        const calls = MOCK_MAKE_AUTHENTICATED_REQUEST.mock.calls;
        const lastCall = calls[calls.length - 1];
        expect(lastCall?.[0]).toBe("/api/memory/insights/user-123");
      }
      expect(result.current.data).toEqual(mockInsights);
    });
  });

  describe("useMemoryStats", () => {
    it("should fetch memory statistics for user", async () => {
      const mockStats = {
        lastUpdated: "2024-01-01T10:00:00Z",
        memoryTypes: {
          accommodation: 45,
          destinations: 32,
          flights: 38,
        },
        storageSize: 1024000,
        totalMemories: 150,
      };

      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValueOnce(mockStats);

      const { result } = renderHook(() => useMemoryStats("user-123"), {
        wrapper: CREATE_WRAPPER(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(MOCK_MAKE_AUTHENTICATED_REQUEST).toHaveBeenCalled();
      {
        const calls = MOCK_MAKE_AUTHENTICATED_REQUEST.mock.calls;
        const lastCall = calls[calls.length - 1];
        expect(lastCall?.[0]).toBe("/api/memory/stats/user-123");
      }
      expect(result.current.data).toEqual(mockStats);
    });
  });

  describe("Hook Integration", () => {
    it("should work together in memory workflow", async () => {
      // Test a complete workflow: store conversation -> get context -> search memories
      const storeResponse = { memory_id: "mem-123", status: "success" };
      const contextResponse = {
        memories: [{ content: "Test memory", id: "mem-123", metadata: {}, score: 0.9 }],
        preferences: {},
        travel_patterns: {},
      };
      const searchResponse = [{ content: "Found memory", metadata: {}, score: 0.8 }];

      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValueOnce(storeResponse) // for store
        .mockResolvedValueOnce(contextResponse) // for context
        .mockResolvedValueOnce(searchResponse); // for search

      // Store conversation
      const { result: storeResult } = renderHook(() => useAddConversationMemory(), {
        wrapper: CREATE_WRAPPER(),
      });

      storeResult.current.mutate({
        messages: [
          { content: "test", role: "user", timestamp: "2024-01-01T10:00:00Z" },
        ],
        sessionId: "test",
        userId: "user-123",
      });

      await waitFor(() => {
        expect(storeResult.current.isSuccess).toBe(true);
      });

      // Get context
      const { result: contextResult } = renderHook(() => useMemoryContext("user-123"), {
        wrapper: CREATE_WRAPPER(),
      });

      await waitFor(() => {
        expect(contextResult.current.isSuccess).toBe(true);
      });

      // Search memories
      const { result: searchResult } = renderHook(() => useSearchMemories(), {
        wrapper: CREATE_WRAPPER(),
      });

      // Need to call mutate for the search
      searchResult.current.mutate({
        query: "test",
        userId: "user-123",
      });

      await waitFor(() => {
        expect(searchResult.current.isSuccess).toBe(true);
      });

      // Verify all operations completed successfully
      expect(storeResult.current.data).toEqual(storeResponse);
      expect(contextResult.current.data).toEqual(contextResponse);
      expect(searchResult.current.data).toEqual(searchResponse);
    });
  });
});
