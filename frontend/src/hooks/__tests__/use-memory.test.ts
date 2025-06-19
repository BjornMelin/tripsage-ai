/**
 * Tests for memory hooks - frontend API integration
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import React, { type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  useMemoryContext,
  useMemoryInsights,
  useMemoryStats,
  useSearchMemories,
  useStoreConversation,
  useUpdatePreferences,
} from "../use-memory";

// Mock the useAuthenticatedApi hook
const mockMakeAuthenticatedRequest = vi.fn();
vi.mock("../use-authenticated-api", () => ({
  useAuthenticatedApi: () => ({
    makeAuthenticatedRequest: mockMakeAuthenticatedRequest,
    isAuthenticated: true,
  }),
}));

// Test wrapper with QueryClient
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function TestWrapper({ children }: { children: ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
};

describe("Memory Hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockMakeAuthenticatedRequest.mockClear();
  });

  describe("useMemoryContext", () => {
    it("should fetch memory context for user", async () => {
      const mockResponse = {
        memories: [
          {
            id: "mem-1",
            content: "User prefers luxury hotels",
            metadata: { category: "accommodation", preference: "luxury" },
            score: 0.95,
            created_at: "2024-01-01T10:00:00Z",
          },
        ],
        preferences: {
          accommodation: "luxury",
          budget: "high",
          destinations: ["Europe", "Asia"],
        },
        travel_patterns: {
          favorite_destinations: ["Paris", "Tokyo"],
          avg_trip_duration: 7,
          booking_lead_time: 30,
        },
      };

      mockMakeAuthenticatedRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(() => useMemoryContext("user-123"), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockMakeAuthenticatedRequest).toHaveBeenCalledWith(
        "/api/memory/context/user-123",
        { params: {} }
      );
      expect(result.current.data).toEqual(mockResponse);
    });

    it("should not fetch when userId is empty", () => {
      const { result } = renderHook(() => useMemoryContext(""), {
        wrapper: createWrapper(),
      });

      expect(mockMakeAuthenticatedRequest).not.toHaveBeenCalled();
      expect(result.current.data).toBeUndefined();
      // When enabled is false in react-query, the query may still show as pending initially
      // but it won't actually fetch data
      expect(result.current.isSuccess).toBe(false);
      expect(result.current.isError).toBe(false);
    });

    it("should handle API errors gracefully", async () => {
      mockMakeAuthenticatedRequest.mockRejectedValueOnce(new Error("API Error"));

      const { result } = renderHook(() => useMemoryContext("user-123"), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeInstanceOf(Error);
    });
  });

  describe("useSearchMemories", () => {
    it("should search memories with query and filters", async () => {
      const mockResults = [
        {
          content: "Looking for flights to Paris",
          metadata: { type: "search", destination: "Paris" },
          score: 0.88,
        },
        {
          content: "Booked luxury hotel in Tokyo",
          metadata: { type: "booking", destination: "Tokyo" },
          score: 0.82,
        },
      ];

      mockMakeAuthenticatedRequest.mockResolvedValueOnce(mockResults);

      const { result } = renderHook(() => useSearchMemories(), {
        wrapper: createWrapper(),
      });

      // Since useSearchMemories returns a mutation, we need to call mutate
      const searchParams = {
        userId: "user-123",
        query: "travel preferences",
        limit: 10,
        filters: { category: "accommodation" },
      };

      result.current.mutate(searchParams);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockMakeAuthenticatedRequest).toHaveBeenCalledWith("/api/memory/search", {
        method: "POST",
        body: JSON.stringify(searchParams),
        headers: { "Content-Type": "application/json" },
      });
      expect(result.current.data).toEqual(mockResults);
    });

    it("should handle search without filters", async () => {
      mockMakeAuthenticatedRequest.mockResolvedValueOnce([]);

      const { result } = renderHook(() => useSearchMemories(), {
        wrapper: createWrapper(),
      });

      const searchParams = {
        userId: "user-123",
        query: "hotels",
        limit: 20, // default limit
      };

      result.current.mutate(searchParams);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockMakeAuthenticatedRequest).toHaveBeenCalledWith("/api/memory/search", {
        method: "POST",
        body: JSON.stringify(searchParams),
        headers: { "Content-Type": "application/json" },
      });
    });
  });

  describe("useStoreConversation", () => {
    it("should store conversation memory", async () => {
      const mockResponse = { status: "success", memory_id: "mem-123" };
      mockMakeAuthenticatedRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(() => useStoreConversation(), {
        wrapper: createWrapper(),
      });

      const conversationData = {
        messages: [
          {
            role: "user" as const,
            content: "I want to book a hotel in Paris",
            timestamp: "2024-01-01T10:00:00Z",
          },
          {
            role: "assistant" as const,
            content: "I can help you find hotels in Paris.",
            timestamp: "2024-01-01T10:01:00Z",
          },
        ],
        userId: "user-123",
        sessionId: "session-123",
      };

      result.current.mutate(conversationData);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockMakeAuthenticatedRequest).toHaveBeenCalledWith(
        "/api/memory/conversations",
        {
          method: "POST",
          body: JSON.stringify(conversationData),
          headers: { "Content-Type": "application/json" },
        }
      );
      expect(result.current.data).toEqual(mockResponse);
    });

    it("should handle conversation storage errors", async () => {
      mockMakeAuthenticatedRequest.mockRejectedValueOnce(new Error("Storage failed"));

      const { result } = renderHook(() => useStoreConversation(), {
        wrapper: createWrapper(),
      });

      const conversationData = {
        messages: [],
        userId: "test",
        sessionId: "test",
      };

      result.current.mutate(conversationData);

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeInstanceOf(Error);
    });
  });

  describe("useUpdatePreferences", () => {
    it("should update user preferences", async () => {
      const mockResponse = { status: "success" };
      mockMakeAuthenticatedRequest.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(() => useUpdatePreferences("user-123"), {
        wrapper: createWrapper(),
      });

      const preferencesData = {
        userId: "user-123",
        preferences: {
          accommodation: "luxury",
          budget: "high",
          destinations: ["Europe"],
        },
      };

      result.current.mutate(preferencesData);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockMakeAuthenticatedRequest).toHaveBeenCalledWith(
        "/api/memory/preferences/user-123",
        {
          method: "POST",
          body: JSON.stringify(preferencesData),
          headers: { "Content-Type": "application/json" },
        }
      );
      expect(result.current.data).toEqual(mockResponse);
    });
  });

  describe("useMemoryInsights", () => {
    it("should fetch memory insights for user", async () => {
      const mockInsights = {
        travel_personality: "luxury_traveler",
        budget_patterns: {
          avg_hotel_budget: 300,
          avg_flight_budget: 800,
          budget_consistency: 0.85,
        },
        destination_preferences: {
          preferred_regions: ["Europe", "Asia"],
          climate_preference: "temperate",
          city_vs_nature: 0.7,
        },
        booking_behavior: {
          avg_lead_time: 45,
          flexible_dates: true,
          price_sensitivity: 0.6,
        },
        ai_recommendations: [
          "Consider luxury hotels in Kyoto for your next trip",
          "Book flights 6-8 weeks in advance for best prices",
        ],
      };

      mockMakeAuthenticatedRequest.mockResolvedValueOnce(mockInsights);

      const { result } = renderHook(() => useMemoryInsights("user-123"), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockMakeAuthenticatedRequest).toHaveBeenCalledWith(
        "/api/memory/insights/user-123",
        { params: {} }
      );
      expect(result.current.data).toEqual(mockInsights);
    });
  });

  describe("useMemoryStats", () => {
    it("should fetch memory statistics for user", async () => {
      const mockStats = {
        totalMemories: 150,
        memoryTypes: {
          accommodation: 45,
          flights: 38,
          destinations: 32,
        },
        lastUpdated: "2024-01-01T10:00:00Z",
        storageSize: 1024000,
      };

      mockMakeAuthenticatedRequest.mockResolvedValueOnce(mockStats);

      const { result } = renderHook(() => useMemoryStats("user-123"), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockMakeAuthenticatedRequest).toHaveBeenCalledWith(
        "/api/memory/stats/user-123",
        { params: {} }
      );
      expect(result.current.data).toEqual(mockStats);
    });
  });

  describe("Hook Integration", () => {
    it("should work together in memory workflow", async () => {
      // Test a complete workflow: store conversation -> get context -> search memories
      const storeResponse = { status: "success", memory_id: "mem-123" };
      const contextResponse = {
        memories: [{ id: "mem-123", content: "Test memory", metadata: {}, score: 0.9 }],
        preferences: {},
        travel_patterns: {},
      };
      const searchResponse = [{ content: "Found memory", metadata: {}, score: 0.8 }];

      mockMakeAuthenticatedRequest
        .mockResolvedValueOnce(storeResponse) // for store
        .mockResolvedValueOnce(contextResponse) // for context
        .mockResolvedValueOnce(searchResponse); // for search

      // Store conversation
      const { result: storeResult } = renderHook(() => useStoreConversation(), {
        wrapper: createWrapper(),
      });

      storeResult.current.mutate({
        messages: [
          { role: "user", content: "test", timestamp: "2024-01-01T10:00:00Z" },
        ],
        userId: "user-123",
        sessionId: "test",
      });

      await waitFor(() => {
        expect(storeResult.current.isSuccess).toBe(true);
      });

      // Get context
      const { result: contextResult } = renderHook(() => useMemoryContext("user-123"), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(contextResult.current.isSuccess).toBe(true);
      });

      // Search memories
      const { result: searchResult } = renderHook(() => useSearchMemories(), {
        wrapper: createWrapper(),
      });

      // Need to call mutate for the search
      searchResult.current.mutate({
        userId: "user-123",
        query: "test",
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
