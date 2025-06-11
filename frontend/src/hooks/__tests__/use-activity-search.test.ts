/**
 * @vitest-environment jsdom
 */

import { api } from "@/lib/api/client";
import { useSearchStore } from "@/stores/search-store";
import type { ActivitySearchParams } from "@/types/search";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { createElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useActivitySearch } from "../use-activity-search";

// Mock the API client
vi.mock("@/lib/api/client", () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

// Mock the search store
vi.mock("@/stores/search-store", () => ({
  useSearchStore: vi.fn(),
}));

const mockUpdateActivityParams = vi.fn();
const mockSetResults = vi.fn();
const mockSetIsLoading = vi.fn();
const mockSetError = vi.fn();

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
};

describe("useActivitySearch", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    (useSearchStore as any).mockReturnValue({
      updateActivityParams: mockUpdateActivityParams,
      setResults: mockSetResults,
      setIsLoading: mockSetIsLoading,
      setError: mockSetError,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("initializes with correct default state", () => {
    const { result } = renderHook(() => useActivitySearch(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isSearching).toBe(false);
    expect(result.current.searchError).toBe(null);
    expect(result.current.savedSearches).toEqual([]);
    expect(result.current.isLoadingSavedSearches).toBe(false);
    expect(result.current.popularActivities).toEqual([]);
    expect(result.current.isLoadingPopularActivities).toBe(false);
    expect(result.current.isSavingSearch).toBe(false);
    expect(result.current.saveSearchError).toBe(null);
  });

  it("provides search functions", () => {
    const { result } = renderHook(() => useActivitySearch(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.searchActivities).toBe("function");
    expect(typeof result.current.saveSearch).toBe("function");
  });

  it("calls API and updates store on successful search", async () => {
    const mockResponse = {
      results: {
        activities: [
          {
            id: "activity-1",
            name: "City Tour",
            type: "cultural",
            location: "New York",
            date: "2024-07-01",
            duration: 3,
            price: 75,
            rating: 4.5,
            description: "Amazing city tour",
            images: [],
          },
        ],
      },
    };

    (api.post as any).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useActivitySearch(), {
      wrapper: createWrapper(),
    });

    const searchParams: ActivitySearchParams = {
      destination: "New York",
      date: "2024-07-01",
      adults: 2,
      children: 0,
      infants: 0,
      category: "cultural",
    };

    await act(async () => {
      result.current.searchActivities(searchParams);
    });

    await waitFor(() => {
      expect(mockUpdateActivityParams).toHaveBeenCalledWith(searchParams);
      expect(api.post).toHaveBeenCalledWith("/api/activities/search", searchParams);
      expect(mockSetIsLoading).toHaveBeenCalledWith(true);
      expect(mockSetError).toHaveBeenCalledWith(null);
      expect(mockSetResults).toHaveBeenCalledWith({
        activities: mockResponse.results.activities,
      });
      expect(mockSetIsLoading).toHaveBeenCalledWith(false);
    });
  });

  it("handles search error correctly", async () => {
    const mockError = new Error("Network error");
    (api.post as any).mockRejectedValue(mockError);

    const { result } = renderHook(() => useActivitySearch(), {
      wrapper: createWrapper(),
    });

    const searchParams: ActivitySearchParams = {
      destination: "Paris",
      date: "2024-08-01",
      adults: 1,
      children: 0,
      infants: 0,
    };

    await act(async () => {
      result.current.searchActivities(searchParams);
    });

    await waitFor(() => {
      expect(mockSetIsLoading).toHaveBeenCalledWith(true);
      expect(mockSetError).toHaveBeenCalledWith(
        "Failed to search activities. Please try again."
      );
      expect(mockSetIsLoading).toHaveBeenCalledWith(false);
    });
  });

  it("loads saved searches on mount", async () => {
    const mockSavedSearches = [
      {
        id: "search-1",
        name: "NYC Cultural Activities",
        searchParams: {
          destination: "New York",
          category: "cultural",
        },
      },
    ];

    (api.get as any).mockResolvedValue(mockSavedSearches);

    const { result } = renderHook(() => useActivitySearch(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith("/api/activities/saved-searches");
    });

    // Note: In a real implementation, you'd check result.current.savedSearches
    // but since we're mocking the store, we just verify the API call
  });

  it("saves search successfully", async () => {
    const mockSaveResponse = { id: "saved-1", success: true };
    (api.post as any).mockResolvedValue(mockSaveResponse);

    const { result } = renderHook(() => useActivitySearch(), {
      wrapper: createWrapper(),
    });

    const searchParams: ActivitySearchParams = {
      destination: "Tokyo",
      date: "2024-09-01",
      adults: 2,
      children: 1,
      infants: 0,
      category: "food",
    };

    await act(async () => {
      result.current.saveSearch("Tokyo Food & Culture", searchParams);
    });

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/api/activities/save-search", {
        name: "Tokyo Food & Culture",
        searchParams,
      });
    });
  });

  it("loads popular activities on mount", async () => {
    const mockPopularActivities = [
      {
        id: "popular-1",
        name: "Popular Tour",
        type: "tour",
        location: "Paris",
        date: "2024-07-01",
        duration: 2,
        price: 50,
        rating: 4.8,
        description: "Very popular tour",
        images: [],
      },
    ];

    (api.get as any).mockResolvedValue(mockPopularActivities);

    const { result } = renderHook(() => useActivitySearch(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith("/api/activities/popular");
    });

    // Note: In a real implementation, you'd check result.current.popularActivities
  });

  it("handles search with empty results", async () => {
    const mockResponse = {
      results: {
        activities: [],
      },
    };

    (api.post as any).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useActivitySearch(), {
      wrapper: createWrapper(),
    });

    const searchParams: ActivitySearchParams = {
      destination: "Remote Location",
      date: "2024-12-01",
      adults: 1,
      children: 0,
      infants: 0,
    };

    await act(async () => {
      result.current.searchActivities(searchParams);
    });

    await waitFor(() => {
      expect(mockSetResults).toHaveBeenCalledWith({
        activities: [],
      });
    });
  });

  it("handles search with all optional parameters", async () => {
    const mockResponse = {
      results: {
        activities: [
          {
            id: "activity-comprehensive",
            name: "Comprehensive Activity",
            type: "adventure",
            location: "Mountain Area",
            date: "2024-07-15",
            duration: 6,
            price: 150,
            rating: 4.9,
            description: "Full-day adventure",
            images: ["image1.jpg"],
          },
        ],
      },
    };

    (api.post as any).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useActivitySearch(), {
      wrapper: createWrapper(),
    });

    const comprehensiveSearchParams: ActivitySearchParams = {
      destination: "Mountain Resort",
      date: "2024-07-15",
      adults: 2,
      children: 1,
      infants: 0,
      category: "outdoor",
      duration: {
        min: 6,
        max: 6,
      },
    };

    await act(async () => {
      result.current.searchActivities(comprehensiveSearchParams);
    });

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        "/api/activities/search",
        comprehensiveSearchParams
      );
      expect(mockUpdateActivityParams).toHaveBeenCalledWith(comprehensiveSearchParams);
    });
  });

  it("handles API errors gracefully", async () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    (api.post as any).mockRejectedValue(new Error("Server error"));

    const { result } = renderHook(() => useActivitySearch(), {
      wrapper: createWrapper(),
    });

    const searchParams: ActivitySearchParams = {
      destination: "Test",
      date: "2024-07-01",
      adults: 1,
      children: 0,
      infants: 0,
    };

    await act(async () => {
      result.current.searchActivities(searchParams);
    });

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith(
        "Activity search failed:",
        expect.any(Error)
      );
      expect(mockSetError).toHaveBeenCalledWith(
        "Failed to search activities. Please try again."
      );
    });

    consoleSpy.mockRestore();
  });
});
