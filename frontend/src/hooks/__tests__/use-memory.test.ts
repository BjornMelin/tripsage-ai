/** @vitest-environment jsdom */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import React, { type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api/error-types";
import type {
  AddConversationMemoryRequest,
  AddConversationMemoryResponse,
  MemoryContextResponse,
  MemoryInsightsResponse,
  SearchMemoriesRequest,
  SearchMemoriesResponse,
  UpdatePreferencesRequest,
  UpdatePreferencesResponse,
} from "@/lib/schemas/memory";
import {
  useAddConversationMemory,
  useMemoryContext,
  useMemoryInsights,
  useMemoryStats,
  useSearchMemories,
  useUpdatePreferences,
} from "../use-memory";

// Mock the useAuthenticatedApi hook with sync responses
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
    vi.useRealTimers();
    vi.clearAllMocks();
    MOCK_MAKE_AUTHENTICATED_REQUEST.mockReset();
  });

  describe("useMemoryContext", () => {
    const renderContext = (userId = "user-123", enabled = true) =>
      renderHook(() => useMemoryContext(userId, enabled), {
        wrapper: CREATE_WRAPPER(),
      });

    it("should fetch memory context for user", async () => {
      const mockResponse: MemoryContextResponse = {
        context: {
          insights: [],
          recentMemories: [],
          travelPatterns: {
            averageBudget: 1200,
            frequentDestinations: [],
            preferredTravelStyle: "luxury",
            seasonalPatterns: {},
          },
          userPreferences: {},
        },
        metadata: {
          lastUpdated: "2024-01-01T00:00:00Z",
          totalMemories: 0,
        },
        success: true,
      };
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValueOnce(mockResponse);

      const { result } = renderContext();

      await waitFor(() => expect(result.current.data).toEqual(mockResponse));
      expect(MOCK_MAKE_AUTHENTICATED_REQUEST).toHaveBeenCalledWith(
        "/api/memory/context/user-123"
      );
    });

    it("should not fetch when userId is empty", () => {
      renderContext("");
      expect(MOCK_MAKE_AUTHENTICATED_REQUEST).not.toHaveBeenCalled();
    });

    it("should handle API errors gracefully", async () => {
      const apiError = new ApiError({ message: "Unauthorized", status: 401 });
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockRejectedValueOnce(apiError);

      const { result } = renderContext();
      await waitFor(() => expect(result.current.error).toBeInstanceOf(ApiError));
      expect(result.current.error?.message).toBe("Unauthorized");
    });
  });

  describe("useSearchMemories", () => {
    const renderSearch = () =>
      renderHook(() => useSearchMemories(), {
        wrapper: CREATE_WRAPPER(),
      });

    it("should post queries with filters", async () => {
      const mockResults: SearchMemoriesResponse = {
        memories: [],
        searchMetadata: {
          queryProcessed: "travel preferences",
          searchTimeMs: 12,
          similarityThresholdUsed: 0.8,
        },
        success: true,
        totalFound: 0,
      };
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValueOnce(mockResults);

      const { result } = renderSearch();
      const searchParams: SearchMemoriesRequest = {
        filters: {
          metadata: { category: "accommodation" },
          type: ["accommodation"],
        },
        limit: 10,
        query: "travel preferences",
        userId: "user-123",
      };

      await act(async () => {
        const data = await result.current.mutateAsync(searchParams);
        expect(data).toEqual(mockResults);
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

    it("should allow minimal query payloads", async () => {
      const minimalResults: SearchMemoriesResponse = {
        memories: [],
        searchMetadata: {
          queryProcessed: "hotels",
          searchTimeMs: 5,
          similarityThresholdUsed: 0.5,
        },
        success: true,
        totalFound: 0,
      };
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValueOnce(minimalResults);

      const { result } = renderSearch();
      const params: SearchMemoriesRequest = {
        limit: 20,
        query: "hotels",
        userId: "user-123",
      };

      await act(async () => {
        await result.current.mutateAsync(params);
      });

      expect(MOCK_MAKE_AUTHENTICATED_REQUEST).toHaveBeenCalledWith(
        "/api/memory/search",
        {
          body: JSON.stringify(params),
          headers: { "Content-Type": "application/json" },
          method: "POST",
        }
      );
    });
  });

  describe("useAddConversationMemory", () => {
    const conversationData: AddConversationMemoryRequest = {
      messages: [
        {
          content: "I want to book a hotel in Paris",
          metadata: undefined,
          role: "user",
          timestamp: "2024-01-01T10:00:00Z",
        },
        {
          content: "I can help you find hotels in Paris.",
          metadata: undefined,
          role: "assistant",
          timestamp: "2024-01-01T10:01:00Z",
        },
      ],
      sessionId: "session-123",
      userId: "user-123",
    };

    const renderAddConversation = () =>
      renderHook(() => useAddConversationMemory(), {
        wrapper: CREATE_WRAPPER(),
      });

    it("should store conversation memory", async () => {
      const mockResponse = {
        insightsGenerated: [],
        memoriesCreated: ["mem-123"],
        metadata: { extractionMethod: "test", processingTimeMs: 10 },
        success: true,
        updatedPreferences: {},
      } satisfies AddConversationMemoryResponse;
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValueOnce(mockResponse);

      const { result } = renderAddConversation();

      await act(async () => {
        const data = await result.current.mutateAsync(conversationData);
        expect(data).toEqual(mockResponse);
      });

      expect(MOCK_MAKE_AUTHENTICATED_REQUEST).toHaveBeenCalledWith(
        "/api/memory/conversations",
        {
          body: JSON.stringify(conversationData),
          headers: { "Content-Type": "application/json" },
          method: "POST",
        }
      );
    });

    it("should handle conversation storage errors", async () => {
      const apiError = new ApiError({ message: "Storage failed", status: 500 });
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockRejectedValueOnce(apiError);

      const { result } = renderAddConversation();
      await act(async () => {
        await expect(
          result.current.mutateAsync(conversationData)
        ).resolves.toBeUndefined();
      });
      expect(MOCK_MAKE_AUTHENTICATED_REQUEST).toHaveBeenCalledWith(
        "/api/memory/conversations",
        expect.objectContaining({ method: "POST" })
      );
    });
  });

  describe("useUpdatePreferences", () => {
    it("should update user preferences", async () => {
      const mockResponse = {
        changesMade: ["accommodation"],
        metadata: { updatedAt: "2024-01-01T00:00:00Z", version: 1 },
        success: true,
        updatedPreferences: {},
      } satisfies UpdatePreferencesResponse;
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(() => useUpdatePreferences("user-123"), {
        wrapper: CREATE_WRAPPER(),
      });

      const preferencesData: UpdatePreferencesRequest = {
        preferences: {
          accommodationType: ["luxury"],
          travelStyle: "premium",
        },
      };

      await act(async () => {
        const data = await result.current.mutateAsync(preferencesData);
        expect(data).toEqual(mockResponse);
      });

      expect(MOCK_MAKE_AUTHENTICATED_REQUEST).toHaveBeenCalledWith(
        "/api/memory/preferences/user-123",
        {
          body: JSON.stringify(preferencesData),
          headers: { "Content-Type": "application/json" },
          method: "POST",
        }
      );
    });
  });

  describe("useMemoryInsights", () => {
    const renderInsights = (userId = "user-123") =>
      renderHook(() => useMemoryInsights(userId), {
        wrapper: CREATE_WRAPPER(),
      });

    it("should fetch memory insights for user", async () => {
      const mockInsights: MemoryInsightsResponse = {
        insights: {
          budgetPatterns: {
            averageSpending: {},
            spendingTrends: [],
          },
          destinationPreferences: {
            discoveryPatterns: [],
            topDestinations: [],
          },
          recommendations: [],
          travelPersonality: {
            confidence: 0.9,
            description: "Explorer",
            keyTraits: ["adventurous"],
            type: "explorer",
          },
        },
        metadata: {
          analysisDate: "2024-01-01T00:00:00Z",
          confidenceLevel: 0.9,
          dataCoverageMonths: 12,
        },
        success: true,
      };
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValueOnce(mockInsights);

      const { result } = renderInsights();
      await waitFor(() => expect(result.current.data).toEqual(mockInsights));
      expect(MOCK_MAKE_AUTHENTICATED_REQUEST).toHaveBeenCalledWith(
        "/api/memory/insights/user-123"
      );
    });
  });

  describe("useMemoryStats", () => {
    const renderStats = (userId = "user-123") =>
      renderHook(() => useMemoryStats(userId), {
        wrapper: CREATE_WRAPPER(),
      });

    it("should fetch memory statistics for user", async () => {
      const mockStats = {
        lastUpdated: "2024-01-01T10:00:00Z",
        memoryTypes: { accommodation: 45 },
        storageSize: 1024,
        totalMemories: 150,
      };
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValueOnce(mockStats);

      const { result } = renderStats();
      await waitFor(() => expect(result.current.data).toEqual(mockStats));
      expect(MOCK_MAKE_AUTHENTICATED_REQUEST).toHaveBeenCalledWith(
        "/api/memory/stats/user-123"
      );
    });
  });
});
