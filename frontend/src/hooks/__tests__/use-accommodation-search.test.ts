import { renderHook, waitFor } from "@testing-library/react";
import React, { type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/lib/api/client";
import { useSearchParamsStore } from "@/stores/search-params-store";
import { useSearchResultsStore } from "@/stores/search-results-store";
import { AllTheProviders } from "@/test/test-utils.test";
import { useAccommodationSearch } from "../use-accommodation-search";

// Mock the API
vi.mock("@/lib/api/client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

// Mock the stores
vi.mock("@/stores/search-params-store");
vi.mock("@/stores/search-results-store");

describe("useAccommodationSearch", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const wrapper = ({ children }: { children: ReactNode }) =>
    React.createElement(AllTheProviders, null, children);

  it("should return hook properties", () => {
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

    const { result } = renderHook(() => useAccommodationSearch(), { wrapper });

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

    vi.mocked(api.get).mockResolvedValueOnce(mockSuggestions);

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
      expect(api.get).toHaveBeenCalledWith("/api/accommodations/suggestions");
    });
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

    vi.mocked(api.post).mockResolvedValueOnce(mockResults);

    const mockStartSearch = vi.fn().mockReturnValue("search-123");

    vi.mocked(useSearchParamsStore).mockReturnValue({
      updateAccommodationParams: vi.fn(),
    });

    vi.mocked(useSearchResultsStore).mockReturnValue({
      completeSearch: vi.fn(),
      setSearchError: vi.fn(),
      setSearchResults: vi.fn(),
      startSearch: mockStartSearch,
    });

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

    // Trigger search
    result.current.search(searchParams);

    // Wait for API call
    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/api/accommodations/search", searchParams);
    });
  });

  it("should handle loading state", async () => {
    let resolvePromise!: (value: unknown) => void;
    const promise = new Promise<unknown>((resolve) => {
      resolvePromise = resolve;
    });

    vi.mocked(api.post).mockReturnValueOnce(promise);

    vi.mocked(useSearchParamsStore).mockReturnValue({
      updateAccommodationParams: vi.fn(),
    });

    vi.mocked(useSearchResultsStore).mockReturnValue({
      completeSearch: vi.fn(),
      setSearchError: vi.fn(),
      setSearchResults: vi.fn(),
      startSearch: vi.fn().mockReturnValue("search-123"),
    });

    const { result } = renderHook(() => useAccommodationSearch(), { wrapper });

    expect(result.current.isSearching).toBe(false);

    // Start search
    result.current.search({
      adults: 2,
      checkIn: "2024-03-15",
      checkOut: "2024-03-18",
      children: 0,
      destination: "New York",
      infants: 0,
      rooms: 1,
    });

    await waitFor(() => {
      expect(result.current.isSearching).toBe(true);
    });

    // Resolve the promise
    resolvePromise?.({
      results: [],
      totalResults: 0,
    });

    await waitFor(() => {
      expect(result.current.isSearching).toBe(false);
    });
  });
});
