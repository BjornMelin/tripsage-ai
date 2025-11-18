/** @vitest-environment jsdom */

import type { QueryClient } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "@/lib/api/api-client";
import { useSearchParamsStore } from "@/stores/search-params-store";
import { useSearchResultsStore } from "@/stores/search-results-store";
import {
  createApiTestQueryClient,
  createApiTestWrapper,
  resetStoreState,
} from "@/test/api-test-helpers";
import { useAccommodationSearch } from "../use-accommodation-search";

vi.mock("@/lib/api/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("useAccommodationSearch", () => {
  let queryClient: QueryClient;
  let wrapper: ReturnType<typeof createApiTestWrapper>;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = createApiTestQueryClient();
    wrapper = createApiTestWrapper(queryClient);
    resetStoreState(useSearchParamsStore);
    resetStoreState(useSearchResultsStore);
    vi.mocked(apiClient.get).mockResolvedValue([]);
    vi.mocked(apiClient.post).mockResolvedValue({ results: [], totalResults: 0 });
  });

  afterEach(() => {
    queryClient.clear();
  });

  it("returns default hook state and suggestions", () => {
    queryClient.setQueryData(["accommodation-suggestions"], []);

    const { result } = renderHook(() => useAccommodationSearch(), { wrapper });

    expect(result.current.suggestions).toEqual([]);
    expect(typeof result.current.search).toBe("function");
    expect(typeof result.current.searchAsync).toBe("function");
    expect(result.current.isSearching).toBe(false);
    expect(result.current.searchError).toBeNull();
  });

  it("fetches accommodation suggestions", () => {
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
    vi.mocked(apiClient.get).mockImplementation(async () => mockSuggestions);
    queryClient.removeQueries({
      exact: true,
      queryKey: ["accommodation-suggestions"],
    });

    const { result, rerender } = renderHook(() => useAccommodationSearch(), {
      wrapper,
    });

    expect(result.current.isSuggestionsLoading).toBe(true);

    act(() => {
      queryClient.setQueryData(["accommodation-suggestions"], mockSuggestions);
    });

    rerender();

    expect(result.current.suggestions).toEqual(mockSuggestions);
    expect(result.current.isSuggestionsLoading).toBe(false);
  });

  it("updates accommodation parameters via the store", async () => {
    const { result } = renderHook(() => useAccommodationSearch(), { wrapper });
    const newParams = { adults: 3, destination: "London" };

    await act(async () => {
      await result.current.updateParams(newParams);
    });

    expect(useSearchParamsStore.getState().accommodationParams).toMatchObject(
      newParams
    );
  });

  it("handles API search requests and stores results", async () => {
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

    const response = await result.current.searchAsync(searchParams);
    expect(response).toEqual(mockResults);
    expect(apiClient.post).toHaveBeenCalledWith("/accommodations/search", searchParams);

    const storeState = useSearchResultsStore.getState();
    expect(storeState.currentSearchType).toBe("accommodation");
    expect(storeState.currentSearchId).toBeTruthy();
    expect(storeState.isSearching).toBe(true);

    const currentSearchId = storeState.currentSearchId;
    expect(currentSearchId).toBeTruthy();
    if (!currentSearchId) {
      throw new Error("Search ID should be defined after calling searchAsync");
    }

    act(() => {
      useSearchResultsStore
        .getState()
        .setSearchResults(currentSearchId, { accommodations: mockResults.results });
      useSearchResultsStore.getState().completeSearch(currentSearchId);
    });

    const latestState = useSearchResultsStore.getState();
    expect(latestState.results.accommodations).toEqual(mockResults.results);
    expect(latestState.status).toBe("success");
    expect(latestState.isSearching).toBe(false);
  });
});
