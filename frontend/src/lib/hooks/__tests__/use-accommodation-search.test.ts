import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useAccommodationSearch } from "../use-accommodation-search";
import { useSearchStore } from "@/stores/search-store";
import { api } from "@/lib/api/client";

// Mock dependencies
vi.mock("@/lib/api/client", () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

vi.mock("@/stores/search-store", () => ({
  useSearchStore: vi.fn(),
}));

describe("useAccommodationSearch", () => {
  let queryClient: QueryClient;
  const mockUpdateAccommodationParams = vi.fn();
  const mockSetResults = vi.fn();
  const mockSetIsLoading = vi.fn();
  const mockSetError = vi.fn();

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    vi.clearAllMocks();

    // Mock store functions
    (useSearchStore as any).mockReturnValue({
      updateAccommodationParams: mockUpdateAccommodationParams,
      setResults: mockSetResults,
      setIsLoading: mockSetIsLoading,
      setError: mockSetError,
    });
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => {
    const { createElement } = require("react");
    return createElement(QueryClientProvider, { client: queryClient }, children);
  };

  it("should search for accommodations successfully", async () => {
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

    await act(async () => {
      result.current.search(searchParams);
    });

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        "/api/accommodations/search",
        searchParams
      );
      expect(mockSetIsLoading).toHaveBeenCalledWith(true);
      expect(mockSetResults).toHaveBeenCalledWith({
        accommodations: mockResults.results,
      });
      expect(mockSetIsLoading).toHaveBeenCalledWith(false);
    });
  });

  it("should handle search errors", async () => {
    const mockError = new Error("Search failed");
    (api.post as any).mockRejectedValueOnce(mockError);

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

    await act(async () => {
      result.current.search(searchParams);
    });

    await waitFor(() => {
      expect(mockSetError).toHaveBeenCalledWith("Search failed");
      expect(mockSetIsLoading).toHaveBeenCalledWith(false);
    });
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

    const { result } = renderHook(() => useAccommodationSearch(), { wrapper });

    await waitFor(() => {
      expect(result.current.suggestions).toEqual(mockSuggestions);
      expect(api.get).toHaveBeenCalledWith("/api/accommodations/suggestions");
    });
  });

  it("should update accommodation parameters", () => {
    const { result } = renderHook(() => useAccommodationSearch(), { wrapper });

    const newParams = { destination: "London", adults: 3 };
    result.current.updateParams(newParams);

    expect(mockUpdateAccommodationParams).toHaveBeenCalledWith(newParams);
  });

  it("should handle search loading state", async () => {
    let resolvePromise: (value: any) => void;
    const promise = new Promise((resolve) => {
      resolvePromise = resolve;
    });
    
    (api.post as any).mockReturnValueOnce(promise);

    const { result } = renderHook(() => useAccommodationSearch(), { wrapper });

    expect(result.current.isSearching).toBe(false);

    act(() => {
      result.current.search({
        destination: "New York",
        startDate: "2024-03-15",
        endDate: "2024-03-18",
        adults: 2,
        children: 0,
        infants: 0,
        rooms: 1,
      });
    });

    await waitFor(() => {
      expect(result.current.isSearching).toBe(true);
    });

    // Resolve the promise
    await act(async () => {
      resolvePromise!({
        results: [],
        totalResults: 0,
      });
    });

    await waitFor(() => {
      expect(result.current.isSearching).toBe(false);
    });
  });
});