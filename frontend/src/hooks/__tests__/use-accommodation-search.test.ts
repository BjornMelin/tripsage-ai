import { api } from "@/lib/api/client";
import { useSearchParamsStore } from "@/stores/search-params-store";
import { useSearchResultsStore } from "@/stores/search-results-store";
import { renderHook, waitFor } from "@testing-library/react";
import React, { type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AllTheProviders } from "@/test/test-utils";
import { useAccommodationSearch } from "../use-accommodation-search";

// Mock the API
vi.mock("@/lib/api/client", () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
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

    (useSearchParamsStore as any).mockReturnValue({
      updateAccommodationParams: mockUpdateAccommodationParams,
    });

    (useSearchResultsStore as any).mockReturnValue({
      startSearch: mockStartSearch,
      setSearchResults: mockSetSearchResults,
      setSearchError: mockSetSearchError,
      completeSearch: mockCompleteSearch,
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
        id: "1",
        name: "Popular Hotel",
        type: "Hotel",
        location: "Paris",
        checkIn: "",
        checkOut: "",
        pricePerNight: 200,
        totalPrice: 0,
        rating: 4.8,
        amenities: ["wifi", "spa"],
        images: [],
      },
    ];

    (api.get as any).mockResolvedValueOnce(mockSuggestions);

    (useSearchParamsStore as any).mockReturnValue({
      updateAccommodationParams: vi.fn(),
    });

    (useSearchResultsStore as any).mockReturnValue({
      startSearch: vi.fn(),
      setSearchResults: vi.fn(),
      setSearchError: vi.fn(),
      completeSearch: vi.fn(),
    });

    const { result } = renderHook(() => useAccommodationSearch(), { wrapper });

    await waitFor(() => {
      expect(result.current.suggestions).toEqual(mockSuggestions);
      expect(api.get).toHaveBeenCalledWith("/api/accommodations/suggestions");
    });
  });

  it("should update accommodation parameters", () => {
    const mockUpdateAccommodationParams = vi.fn();

    (useSearchParamsStore as any).mockReturnValue({
      updateAccommodationParams: mockUpdateAccommodationParams,
    });

    (useSearchResultsStore as any).mockReturnValue({
      startSearch: vi.fn(),
      setSearchResults: vi.fn(),
      setSearchError: vi.fn(),
      completeSearch: vi.fn(),
    });

    const { result } = renderHook(() => useAccommodationSearch(), { wrapper });

    const newParams = { destination: "London", adults: 3 };
    result.current.updateParams(newParams);

    expect(mockUpdateAccommodationParams).toHaveBeenCalledWith(newParams);
  });

  it("should handle API post requests", async () => {
    const mockResults = {
      results: [
        {
          id: "1",
          name: "Test Hotel",
          type: "Hotel",
          location: "New York",
          checkIn: "2024-03-15",
          checkOut: "2024-03-18",
          pricePerNight: 150,
          totalPrice: 450,
          rating: 4.5,
          amenities: ["wifi", "breakfast"],
          images: [],
        },
      ],
      totalResults: 1,
    };

    (api.post as any).mockResolvedValueOnce(mockResults);

    const mockStartSearch = vi.fn().mockReturnValue("search-123");

    (useSearchParamsStore as any).mockReturnValue({
      updateAccommodationParams: vi.fn(),
    });

    (useSearchResultsStore as any).mockReturnValue({
      startSearch: mockStartSearch,
      setSearchResults: vi.fn(),
      setSearchError: vi.fn(),
      completeSearch: vi.fn(),
    });

    const { result } = renderHook(() => useAccommodationSearch(), { wrapper });

    const searchParams = {
      destination: "New York",
      startDate: "2024-03-15",
      endDate: "2024-03-18",
      adults: 2,
      children: 0,
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
    let resolvePromise: (value: any) => void;
    const promise = new Promise((resolve) => {
      resolvePromise = resolve;
    });

    (api.post as any).mockReturnValueOnce(promise);

    (useSearchParamsStore as any).mockReturnValue({
      updateAccommodationParams: vi.fn(),
    });

    (useSearchResultsStore as any).mockReturnValue({
      startSearch: vi.fn().mockReturnValue("search-123"),
      setSearchResults: vi.fn(),
      setSearchError: vi.fn(),
      completeSearch: vi.fn(),
    });

    const { result } = renderHook(() => useAccommodationSearch(), { wrapper });

    expect(result.current.isSearching).toBe(false);

    // Start search
    result.current.search({
      destination: "New York",
      startDate: "2024-03-15",
      endDate: "2024-03-18",
      adults: 2,
      children: 0,
      infants: 0,
      rooms: 1,
    });

    await waitFor(() => {
      expect(result.current.isSearching).toBe(true);
    });

    // Resolve the promise
    resolvePromise!({
      results: [],
      totalResults: 0,
    });

    await waitFor(() => {
      expect(result.current.isSearching).toBe(false);
    });
  });
});