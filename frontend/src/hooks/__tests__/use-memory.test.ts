import {
  QueryClient,
  QueryClientProvider,
  type QueryFunction,
  type QueryFunctionContext,
  type UseMutationOptions,
  type UseQueryOptions,
  useMutation,
  useQuery,
} from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import React, { type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, type AppError } from "@/lib/api/error-types";
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

// Spy on useQuery and useMutation to inspect options passed to them
vi.mock("@tanstack/react-query", async () => {
  const actual = await vi.importActual<typeof import("@tanstack/react-query")>(
    "@tanstack/react-query"
  );
  return Object.assign(actual, {
    useMutation: vi.fn((...args: Parameters<typeof actual.useMutation>) =>
      actual.useMutation(...args)
    ),
    useQuery: vi.fn((...args: Parameters<typeof actual.useQuery>) =>
      actual.useQuery(...args)
    ),
  });
});

const useQueryMock = vi.mocked(useQuery);
const useMutationMock = vi.mocked(useMutation);

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
    MOCK_MAKE_AUTHENTICATED_REQUEST.mockReset();
  });

  describe("useMemoryContext", () => {
    const getLastQueryOptions = () => {
      const call = useQueryMock.mock.calls.at(-1);
      expect(call).toBeDefined();
      return call?.[0] as unknown as UseQueryOptions<
        MemoryContextResponse,
        AppError,
        MemoryContextResponse,
        ["memory", "context", string]
      >;
    };

    it("should fetch memory context for user", async () => {
      const mockResponse = {
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
      } as MemoryContextResponse;
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValueOnce(mockResponse);

      renderHook(() => useMemoryContext("user-123"), {
        wrapper: CREATE_WRAPPER(),
      });

      const options = getLastQueryOptions();
      expect(options?.enabled).toBe(true);
      expect(options?.queryKey).toEqual(["memory", "context", "user-123"]);

      const queryFn = options?.queryFn as QueryFunction<
        MemoryContextResponse,
        ["memory", "context", string]
      >;
      const data = await queryFn?.({
        queryKey: options?.queryKey as ["memory", "context", string],
      } as QueryFunctionContext<["memory", "context", string]>);
      expect(data).toEqual(mockResponse);
      expect(MOCK_MAKE_AUTHENTICATED_REQUEST).toHaveBeenCalledWith(
        "/api/memory/context/user-123"
      );
    });

    it("should not fetch when userId is empty", () => {
      renderHook(() => useMemoryContext(""), {
        wrapper: CREATE_WRAPPER(),
      });

      const options = getLastQueryOptions();
      expect(options?.enabled).toBe(false);
      expect(MOCK_MAKE_AUTHENTICATED_REQUEST).not.toHaveBeenCalled();
    });

    it("should handle API errors gracefully", async () => {
      const apiError = new ApiError({ message: "Unauthorized", status: 401 });
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockRejectedValueOnce(apiError);

      renderHook(() => useMemoryContext("user-123"), {
        wrapper: CREATE_WRAPPER(),
      });

      const options = getLastQueryOptions();
      const queryFn = options?.queryFn as QueryFunction<
        MemoryContextResponse,
        ["memory", "context", string]
      >;
      await expect(
        queryFn?.({
          queryKey: options?.queryKey as ["memory", "context", string],
        } as QueryFunctionContext<["memory", "context", string]>)
      ).rejects.toBe(apiError);
    });
  });

  describe("useSearchMemories", () => {
    const getMutationOptions = () => {
      const call = useMutationMock.mock.calls.at(-1);
      expect(call).toBeDefined();
      return call?.[0] as UseMutationOptions<
        SearchMemoriesResponse,
        AppError,
        SearchMemoriesRequest
      >;
    };

    it("should post queries with filters", async () => {
      const mockResults = {
        memories: [],
        searchMetadata: {
          queryProcessed: "travel preferences",
          searchTimeMs: 12,
          similarityThresholdUsed: 0.8,
        },
        success: true,
        totalFound: 0,
      } satisfies SearchMemoriesResponse;
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValueOnce(mockResults);

      renderHook(() => useSearchMemories(), {
        wrapper: CREATE_WRAPPER(),
      });

      const mutation = getMutationOptions();
      const mutate = mutation?.mutationFn as (
        variables: SearchMemoriesRequest
      ) => Promise<SearchMemoriesResponse>;
      const searchParams: SearchMemoriesRequest = {
        filters: {
          metadata: { category: "accommodation" },
          type: ["accommodation"],
        },
        limit: 10,
        query: "travel preferences",
        userId: "user-123",
      };

      const data = await mutate?.(searchParams);

      expect(MOCK_MAKE_AUTHENTICATED_REQUEST).toHaveBeenCalledWith(
        "/api/memory/search",
        {
          body: JSON.stringify(searchParams),
          headers: { "Content-Type": "application/json" },
          method: "POST",
        }
      );
      expect(data).toEqual(mockResults);
    });

    it("should allow minimal query payloads", async () => {
      const minimalResults = {
        memories: [],
        searchMetadata: {
          queryProcessed: "hotels",
          searchTimeMs: 5,
          similarityThresholdUsed: 0.5,
        },
        success: true,
        totalFound: 0,
      } satisfies SearchMemoriesResponse;
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValueOnce(minimalResults);

      renderHook(() => useSearchMemories(), {
        wrapper: CREATE_WRAPPER(),
      });

      const mutation = getMutationOptions();
      const mutate = mutation?.mutationFn as (
        variables: SearchMemoriesRequest
      ) => Promise<SearchMemoriesResponse>;
      const params: SearchMemoriesRequest = {
        limit: 20,
        query: "hotels",
        userId: "user-123",
      };

      await mutate?.(params);

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
    const getMutationOptions = () => {
      const call = useMutationMock.mock.calls.at(-1);
      expect(call).toBeDefined();
      return call?.[0] as UseMutationOptions<
        AddConversationMemoryResponse,
        AppError,
        AddConversationMemoryRequest
      >;
    };

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

    it("should store conversation memory", async () => {
      const mockResponse = {
        insightsGenerated: [],
        memoriesCreated: ["mem-123"],
        metadata: { extractionMethod: "test", processingTimeMs: 10 },
        success: true,
        updatedPreferences: {},
      } satisfies AddConversationMemoryResponse;
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValueOnce(mockResponse);

      renderHook(() => useAddConversationMemory(), {
        wrapper: CREATE_WRAPPER(),
      });

      const mutation = getMutationOptions();
      const mutate = mutation?.mutationFn as (
        vars: AddConversationMemoryRequest
      ) => Promise<AddConversationMemoryResponse>;
      const data = await mutate?.(conversationData);

      expect(MOCK_MAKE_AUTHENTICATED_REQUEST).toHaveBeenCalledWith(
        "/api/memory/conversations",
        {
          body: JSON.stringify(conversationData),
          headers: { "Content-Type": "application/json" },
          method: "POST",
        }
      );
      expect(data).toEqual(mockResponse);
    });

    it("should handle conversation storage errors", async () => {
      const apiError = new ApiError({ message: "Storage failed", status: 500 });
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockRejectedValueOnce(apiError);

      renderHook(() => useAddConversationMemory(), {
        wrapper: CREATE_WRAPPER(),
      });

      const mutation = getMutationOptions();
      const mutate = mutation?.mutationFn as (
        vars: AddConversationMemoryRequest
      ) => Promise<AddConversationMemoryResponse>;
      await expect(mutate?.(conversationData)).rejects.toBe(apiError);
    });
  });

  describe("useUpdatePreferences", () => {
    const getMutationOptions = () => {
      const call = useMutationMock.mock.calls.at(-1);
      expect(call).toBeDefined();
      return call?.[0] as UseMutationOptions<
        UpdatePreferencesResponse,
        AppError,
        UpdatePreferencesRequest
      >;
    };

    it("should update user preferences", async () => {
      const mockResponse = {
        changesMade: ["accommodation"],
        metadata: { updatedAt: "2024-01-01T00:00:00Z", version: 1 },
        success: true,
        updatedPreferences: {},
      } satisfies UpdatePreferencesResponse;
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValueOnce(mockResponse);

      renderHook(() => useUpdatePreferences("user-123"), {
        wrapper: CREATE_WRAPPER(),
      });

      const mutation = getMutationOptions();
      const mutate = mutation?.mutationFn as (
        vars: UpdatePreferencesRequest
      ) => Promise<UpdatePreferencesResponse>;
      const preferencesData: UpdatePreferencesRequest = {
        preferences: {
          accommodationType: ["luxury"],
          travelStyle: "premium",
        },
      };

      const data = await mutate?.(preferencesData);

      expect(MOCK_MAKE_AUTHENTICATED_REQUEST).toHaveBeenCalledWith(
        "/api/memory/preferences/user-123",
        {
          body: JSON.stringify(preferencesData),
          headers: { "Content-Type": "application/json" },
          method: "POST",
        }
      );
      expect(data).toEqual(mockResponse);
    });
  });

  describe("useMemoryInsights", () => {
    const getQueryOptions = () => {
      const call = useQueryMock.mock.calls.at(-1);
      expect(call).toBeDefined();
      return call?.[0] as unknown as UseQueryOptions<
        MemoryInsightsResponse,
        AppError,
        MemoryInsightsResponse,
        ["memory", "insights", string]
      >;
    };

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

      renderHook(() => useMemoryInsights("user-123"), {
        wrapper: CREATE_WRAPPER(),
      });

      const options = getQueryOptions();
      expect(options?.queryKey).toEqual(["memory", "insights", "user-123"]);
      const queryFn = options?.queryFn as QueryFunction<
        MemoryInsightsResponse,
        ["memory", "insights", string]
      >;
      const data = await queryFn?.({
        queryKey: options?.queryKey as ["memory", "insights", string],
      } as QueryFunctionContext<["memory", "insights", string]>);
      expect(MOCK_MAKE_AUTHENTICATED_REQUEST).toHaveBeenCalledWith(
        "/api/memory/insights/user-123"
      );
      expect(data).toEqual(mockInsights);
    });
  });

  describe("useMemoryStats", () => {
    const getQueryOptions = () => {
      const call = useQueryMock.mock.calls.at(-1);
      expect(call).toBeDefined();
      return call?.[0] as unknown as UseQueryOptions<
        {
          lastUpdated: string;
          memoryTypes: Record<string, number>;
          storageSize: number;
          totalMemories: number;
        },
        AppError,
        {
          lastUpdated: string;
          memoryTypes: Record<string, number>;
          storageSize: number;
          totalMemories: number;
        },
        ["memory", "stats", string]
      >;
    };

    it("should fetch memory statistics for user", async () => {
      const mockStats = {
        lastUpdated: "2024-01-01T10:00:00Z",
        memoryTypes: { accommodation: 45 },
        storageSize: 1024,
        totalMemories: 150,
      };
      MOCK_MAKE_AUTHENTICATED_REQUEST.mockResolvedValueOnce(mockStats);

      renderHook(() => useMemoryStats("user-123"), {
        wrapper: CREATE_WRAPPER(),
      });

      const options = getQueryOptions();
      expect(options?.queryKey).toEqual(["memory", "stats", "user-123"]);
      const queryFn = options?.queryFn as QueryFunction<
        {
          lastUpdated: string;
          memoryTypes: Record<string, number>;
          storageSize: number;
          totalMemories: number;
        },
        ["memory", "stats", string]
      >;
      const data = await queryFn?.({
        queryKey: options?.queryKey as ["memory", "stats", string],
      } as QueryFunctionContext<["memory", "stats", string]>);
      expect(MOCK_MAKE_AUTHENTICATED_REQUEST).toHaveBeenCalledWith(
        "/api/memory/stats/user-123"
      );
      expect(data).toEqual(mockStats);
    });
  });
});
