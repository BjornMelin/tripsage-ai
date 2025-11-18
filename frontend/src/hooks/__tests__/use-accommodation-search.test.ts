/** @vitest-environment jsdom */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import React, { type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "@/lib/api/api-client";
import { useSearchParamsStore } from "@/stores/search-params-store";
import { useSearchResultsStore } from "@/stores/search-results-store";
import { useAccommodationSearch } from "../use-accommodation-search";

// Mock the API
vi.mock("@/lib/api/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

// Mock the stores
vi.mock("@/stores/search-params-store");
vi.mock("@/stores/search-results-store");

describe("useAccommodationSearch", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        mutations: { retry: false },
        queries: { gcTime: 0, retry: false, staleTime: 0 },
      },
    });
    vi.mocked(apiClient.get).mockResolvedValue([]);
    vi.mocked(apiClient.post).mockResolvedValue({ results: [], totalResults: 0 });
  });

  const wrapper = ({ children }: { children: ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);

  it("should return hook properties", async () => {
    const mockUpdateAccommodationParams = vi.fn();
    const mockStartSearch = vi.fn().mockReturnValue("search-123");
    const mockSetSearchResults = vi.fn();
    const mockSetSearchError = vi.fn();
    const mockCompleteSearch = vi.fn();

    vi.mocked(useSearchParamsStore).mockReturnValue({
      updateAccommodationParams: mockUpdateAccommodationParams,
    });

    vi.mocked(useSearchResultsStore).mockReturnValue({
      completeSearch: mockCompleteSearch,
      setSearchError: mockSetSearchError,
      setSearchResults: mockSetSearchResults,
      startSearch: mockStartSearch,
    });

    // Pre-populate the query cache with empty suggestions
    queryClient.setQueryData(["accommodation-suggestions"], []);

    const { result } = renderHook(() => useAccommodationSearch(), { wrapper });

    await waitFor(() => {
      expect(result.current.suggestions).toEqual([]);
    });

    // Check that the hook returns the expected properties
    expect(result.current.search).toBeDefined();
    expect(result.current.searchAsync).toBeDefined();
    expect(result.current.isSearching).toBe(false);
    expect(result.current.searchError).toBeNull();
    expect(result.current.updateParams).toBe(mockUpdateAccommodationParams);
  });

  it("should fetch accommodation suggestions", async () => {
    const mockSuggestions = [
      {
        amenities: ["wifi", "spa"],
        checkIn: "",
        checkOut: "",
        id: "1",
        images: [],
        location: "Paris",
        name: "Popular Hotel",
        pricePerNight: 200,
        rating: 4.8,
        totalPrice: 0,
        type: "Hotel",
      },
    ];

    vi.mocked(apiClient.get).mockResolvedValue(mockSuggestions);

    vi.mocked(useSearchParamsStore).mockReturnValue({
      updateAccommodationParams: vi.fn(),
    });

    vi.mocked(useSearchResultsStore).mockReturnValue({
      completeSearch: vi.fn(),
      setSearchError: vi.fn(),
      setSearchResults: vi.fn(),
      startSearch: vi.fn(),
    });

    const { result } = renderHook(() => useAccommodationSearch(), { wrapper });

    await waitFor(() => {
      expect(result.current.suggestions).toEqual(mockSuggestions);
    });

    expect(apiClient.get).toHaveBeenCalledWith("/accommodations/suggestions");
  });

  it("should update accommodation parameters", () => {
    const mockUpdateAccommodationParams = vi.fn();

    vi.mocked(useSearchParamsStore).mockReturnValue({
      updateAccommodationParams: mockUpdateAccommodationParams,
    });

    vi.mocked(useSearchResultsStore).mockReturnValue({
      completeSearch: vi.fn(),
      setSearchError: vi.fn(),
      setSearchResults: vi.fn(),
      startSearch: vi.fn(),
    });

    // Pre-populate the query cache to prevent undefined data errors
    queryClient.setQueryData(["accommodation-suggestions"], []);

    const { result } = renderHook(() => useAccommodationSearch(), { wrapper });

    const newParams = { adults: 3, destination: "London" };
    result.current.updateParams(newParams);

    expect(mockUpdateAccommodationParams).toHaveBeenCalledWith(newParams);
  });

  it("should handle API post requests", async () => {
    const mockResults = {
      results: [
        {
          amenities: ["wifi", "breakfast"],
          checkIn: "2024-03-15",
          checkOut: "2024-03-18",
          id: "1",
          images: [],
          location: "New York",
          name: "Test Hotel",
          pricePerNight: 150,
          rating: 4.5,
          totalPrice: 450,
          type: "Hotel",
        },
      ],
      totalResults: 1,
    };

    vi.mocked(apiClient.post).mockResolvedValue(mockResults);

    const mockStartSearch = vi.fn().mockReturnValue("search-123");
    const mockSetSearchResults = vi.fn();
    const mockCompleteSearch = vi.fn();

    vi.mocked(useSearchParamsStore).mockReturnValue({
      updateAccommodationParams: vi.fn(),
    });

    vi.mocked(useSearchResultsStore).mockReturnValue({
      completeSearch: mockCompleteSearch,
      setSearchError: vi.fn(),
      setSearchResults: mockSetSearchResults,
      startSearch: mockStartSearch,
    });

    // Pre-populate the query cache to prevent undefined data errors
    queryClient.setQueryData(["accommodation-suggestions"], []);

    const { result } = renderHook(() => useAccommodationSearch(), { wrapper });

    const searchParams = {
      adults: 2,
      checkIn: "2024-03-15",
      checkOut: "2024-03-18",
      children: 0,
      destination: "New York",
      infants: 0,
      rooms: 1,
    };

    // Trigger search and wait for completion
    await act(async () => {
      await result.current.searchAsync(searchParams);
    });

    expect(apiClient.post).toHaveBeenCalledWith("/accommodations/search", searchParams);
    await waitFor(() => {
      expect(mockSetSearchResults).toHaveBeenCalledWith("search-123", {
        accommodations: mockResults.results,
      });
      expect(mockCompleteSearch).toHaveBeenCalledWith("search-123");
    });
  });

  it("should handle loading state", async () => {
    let resolvePromise!: (value: unknown) => void;
    const promise = new Promise<unknown>((resolve) => {
      resolvePromise = resolve;
    });

    vi.mocked(apiClient.post).mockReturnValue(promise);

    vi.mocked(useSearchParamsStore).mockReturnValue({
      updateAccommodationParams: vi.fn(),
    });

    vi.mocked(useSearchResultsStore).mockReturnValue({
      completeSearch: vi.fn(),
      setSearchError: vi.fn(),
      setSearchResults: vi.fn(),
      startSearch: vi.fn().mockReturnValue("search-123"),
    });

    // Pre-populate the query cache to prevent undefined data errors
    queryClient.setQueryData(["accommodation-suggestions"], []);

    const { result } = renderHook(() => useAccommodationSearch(), { wrapper });

    expect(result.current.isSearching).toBe(false);

    // Start search
    act(() => {
      result.current.search({
        adults: 2,
        checkIn: "2024-03-15",
        checkOut: "2024-03-18",
        children: 0,
        destination: "New York",
        infants: 0,
        rooms: 1,
      });
    });

    // Loading state should become true
    await waitFor(
      () => {
        expect(result.current.isSearching).toBe(true);
      },
      { timeout: 1000 }
    );

    // Resolve the promise
    act(() => {
      resolvePromise?.({
        results: [],
        totalResults: 0,
      });
    });

    // Wait for promise resolution
    await act(async () => {
      await promise;
    });

    // Should be false after completion
    expect(result.current.isSearching).toBe(false);
  });
});
