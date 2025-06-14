/**
 * @vitest-environment jsdom
 */

import { api } from "@/lib/api/client";
import { useSearchParamsStore } from "@/stores/search-params-store";
import { useSearchResultsStore } from "@/stores/search-results-store";
import type { ActivitySearchParams } from "@/types/search";
import { renderHook, waitFor } from "@testing-library/react";
import React, { type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AllTheProviders } from "@/test/test-utils";
import { useActivitySearch } from "../use-activity-search";

// Mock the API client
vi.mock("@/lib/api/client", () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

// Mock the stores
vi.mock("@/stores/search-params-store");
vi.mock("@/stores/search-results-store");

describe("useActivitySearch", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const wrapper = ({ children }: { children: ReactNode }) =>
    React.createElement(AllTheProviders, null, children);

  it("should return hook properties", () => {
    // Mock empty responses for initial queries
    (api.get as any).mockResolvedValue([]);

    const mockUpdateActivityParams = vi.fn();
    const mockStartSearch = vi.fn().mockReturnValue("search-123");
    const mockSetSearchResults = vi.fn();
    const mockSetSearchError = vi.fn();
    const mockCompleteSearch = vi.fn();

    (useSearchParamsStore as any).mockReturnValue({
      updateActivityParams: mockUpdateActivityParams,
    });

    (useSearchResultsStore as any).mockReturnValue({
      startSearch: mockStartSearch,
      setSearchResults: mockSetSearchResults,
      setSearchError: mockSetSearchError,
      completeSearch: mockCompleteSearch,
    });

    const { result } = renderHook(() => useActivitySearch(), { wrapper });

    // Check that the hook returns the expected properties
    expect(result.current.searchActivities).toBeDefined();
    expect(result.current.saveSearch).toBeDefined();
    expect(result.current.isSearching).toBe(false);
    expect(result.current.searchError).toBeNull();
    expect(result.current.savedSearches).toEqual([]);
    expect(result.current.popularActivities).toEqual([]);
    expect(result.current.isSavingSearch).toBe(false);
    expect(result.current.saveSearchError).toBeNull();
  });

  it("should load saved searches", async () => {
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

    (api.get as any).mockResolvedValueOnce(mockSavedSearches);

    (useSearchParamsStore as any).mockReturnValue({
      updateActivityParams: vi.fn(),
    });

    (useSearchResultsStore as any).mockReturnValue({
      startSearch: vi.fn(),
      setSearchResults: vi.fn(),
      setSearchError: vi.fn(),
      completeSearch: vi.fn(),
    });

    const { result } = renderHook(() => useActivitySearch(), { wrapper });

    await waitFor(() => {
      expect(result.current.savedSearches).toEqual(mockSavedSearches);
      expect(api.get).toHaveBeenCalledWith("/api/activities/saved-searches");
    });
  });

  it("should load popular activities", async () => {
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

    (api.get as any).mockResolvedValueOnce([]);
    (api.get as any).mockResolvedValueOnce(mockPopularActivities);

    (useSearchParamsStore as any).mockReturnValue({
      updateActivityParams: vi.fn(),
    });

    (useSearchResultsStore as any).mockReturnValue({
      startSearch: vi.fn(),
      setSearchResults: vi.fn(),
      setSearchError: vi.fn(),
      completeSearch: vi.fn(),
    });

    const { result } = renderHook(() => useActivitySearch(), { wrapper });

    await waitFor(() => {
      expect(result.current.popularActivities).toEqual(mockPopularActivities);
      expect(api.get).toHaveBeenCalledWith("/api/activities/popular");
    });
  });


  it("should handle API post requests", async () => {
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

    (api.post as any).mockResolvedValueOnce(mockResponse);

    const mockUpdateActivityParams = vi.fn();
    const mockStartSearch = vi.fn().mockReturnValue("search-123");

    (useSearchParamsStore as any).mockReturnValue({
      updateActivityParams: mockUpdateActivityParams,
    });

    (useSearchResultsStore as any).mockReturnValue({
      startSearch: mockStartSearch,
      setSearchResults: vi.fn(),
      setSearchError: vi.fn(),
      completeSearch: vi.fn(),
    });

    const { result } = renderHook(() => useActivitySearch(), { wrapper });

    const searchParams: ActivitySearchParams = {
      destination: "New York",
      date: "2024-07-01",
      adults: 2,
      children: 0,
      infants: 0,
      category: "cultural",
    };

    // Trigger search
    result.current.searchActivities(searchParams);

    // Wait for API call
    await waitFor(() => {
      expect(mockUpdateActivityParams).toHaveBeenCalledWith(searchParams);
      expect(api.post).toHaveBeenCalledWith("/api/activities/search", searchParams);
    });
  });

  it("should save search successfully", async () => {
    const mockSaveResponse = { id: "saved-1", success: true };
    (api.post as any).mockResolvedValueOnce(mockSaveResponse);

    (useSearchParamsStore as any).mockReturnValue({
      updateActivityParams: vi.fn(),
    });

    (useSearchResultsStore as any).mockReturnValue({
      startSearch: vi.fn(),
      setSearchResults: vi.fn(),
      setSearchError: vi.fn(),
      completeSearch: vi.fn(),
    });

    const { result } = renderHook(() => useActivitySearch(), { wrapper });

    const searchParams: ActivitySearchParams = {
      destination: "Tokyo",
      date: "2024-09-01",
      adults: 2,
      children: 1,
      infants: 0,
      category: "food",
    };

    result.current.saveSearch("Tokyo Food & Culture", searchParams);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/api/activities/save-search", {
        name: "Tokyo Food & Culture",
        searchParams,
      });
    });
  });

  it("should handle loading state", async () => {
    let resolvePromise: (value: any) => void;
    const promise = new Promise((resolve) => {
      resolvePromise = resolve;
    });

    (api.post as any).mockReturnValueOnce(promise);

    (useSearchParamsStore as any).mockReturnValue({
      updateActivityParams: vi.fn(),
    });

    (useSearchResultsStore as any).mockReturnValue({
      startSearch: vi.fn().mockReturnValue("search-123"),
      setSearchResults: vi.fn(),
      setSearchError: vi.fn(),
      completeSearch: vi.fn(),
    });

    const { result } = renderHook(() => useActivitySearch(), { wrapper });

    expect(result.current.isSearching).toBe(false);

    // Start search
    result.current.searchActivities({
      destination: "New York",
      date: "2024-07-01",
      adults: 2,
      children: 0,
      infants: 0,
    });

    await waitFor(() => {
      expect(result.current.isSearching).toBe(true);
    });

    // Resolve the promise
    resolvePromise!({
      results: { activities: [] },
    });

    await waitFor(() => {
      expect(result.current.isSearching).toBe(false);
    });
  });
});