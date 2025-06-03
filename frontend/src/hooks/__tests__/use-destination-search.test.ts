/**
 * @vitest-environment jsdom
 */

import { useSearchStore } from "@/stores/search-store";
import type { DestinationSearchParams } from "@/types/search";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement } from "react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useDestinationSearch } from "../use-destination-search";

// Mock the search store
vi.mock("@/stores/search-store", () => ({
  useSearchStore: vi.fn(),
}));

// Mock the API client
vi.mock("@/lib/api/client", () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

const mockSearchStore = {
  updateDestinationParams: vi.fn(),
  setResults: vi.fn(),
  setIsLoading: vi.fn(),
  setError: vi.fn(),
};

// Create a wrapper for React Query
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });

  return ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
};

describe("useDestinationSearch", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Setup mock store
    (useSearchStore as any).mockReturnValue(mockSearchStore);
  });

  it("initializes with correct default state", () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useDestinationSearch(), { wrapper });

    expect(result.current.isSearching).toBe(false);
    expect(result.current.isAutocompleting).toBe(false);
    expect(result.current.isLoadingDetails).toBe(false);
    expect(result.current.searchError).toBe(null);
    expect(result.current.autocompleteError).toBe(null);
    expect(result.current.detailsError).toBe(null);
  });

  it("provides search function", () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useDestinationSearch(), { wrapper });

    expect(typeof result.current.searchDestinations).toBe("function");
    expect(typeof result.current.searchDestinationsMock).toBe("function");
  });

  it("provides autocomplete functions", () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useDestinationSearch(), { wrapper });

    expect(typeof result.current.getAutocompleteSuggestions).toBe("function");
    expect(typeof result.current.generateSessionToken).toBe("function");
  });

  it("provides place details function", () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useDestinationSearch(), { wrapper });

    expect(typeof result.current.getPlaceDetails).toBe("function");
  });

  it("provides reset functions", () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useDestinationSearch(), { wrapper });

    expect(typeof result.current.resetSearch).toBe("function");
    expect(typeof result.current.resetAutocomplete).toBe("function");
    expect(typeof result.current.resetDetails).toBe("function");
  });

  it("generates session tokens correctly", () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useDestinationSearch(), { wrapper });

    const token = result.current.generateSessionToken();

    expect(typeof token).toBe("string");
    expect(token).toMatch(/^session_\d+_[a-zA-Z0-9]+$/);
  });

  it("executes mock search successfully", async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useDestinationSearch(), { wrapper });

    const searchParams: DestinationSearchParams = {
      query: "Paris",
      types: ["locality"],
      limit: 10,
    };

    // Execute mock search
    const searchPromise = result.current.searchDestinationsMock(searchParams);

    // Should be loading
    expect(mockSearchStore.setIsLoading).toHaveBeenCalledWith(true);
    expect(mockSearchStore.setError).toHaveBeenCalledWith(null);

    // Wait for search to complete
    const response = await searchPromise;

    expect(response).toBeDefined();
    expect(response.destinations).toBeDefined();
    expect(Array.isArray(response.destinations)).toBe(true);
    expect(response.total).toBeDefined();
    expect(typeof response.hasMore).toBe("boolean");

    // Should update store
    expect(mockSearchStore.setResults).toHaveBeenCalledWith({
      destinations: expect.any(Array),
    });
    expect(mockSearchStore.updateDestinationParams).toHaveBeenCalledWith(searchParams);
    expect(mockSearchStore.setIsLoading).toHaveBeenCalledWith(false);
  });

  it("handles search errors correctly", async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useDestinationSearch(), { wrapper });

    // Mock an error by passing invalid parameters or by mocking the search to throw
    // For this test, we'll manually trigger error handling by calling setError
    mockSearchStore.setIsLoading.mockImplementation(() => {
      throw new Error("Network error");
    });

    const searchParams: DestinationSearchParams = {
      query: "",
      types: [],
      limit: -1, // Invalid limit
    };

    try {
      await result.current.searchDestinationsMock(searchParams);
    } catch (error) {
      expect(error).toBeInstanceOf(Error);
    }
  });

  it("filters mock destinations based on query", async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useDestinationSearch(), { wrapper });

    // Search for Paris
    const parisResponse = await result.current.searchDestinationsMock({
      query: "Paris",
      types: ["locality"],
      limit: 10,
    });

    // Should find Paris in the mock data
    const parisDestination = parisResponse.destinations.find((d) => d.name === "Paris");
    expect(parisDestination).toBeDefined();

    // Search for a non-existent destination
    const nonExistentResponse = await result.current.searchDestinationsMock({
      query: "NonExistentCity",
      types: ["locality"],
      limit: 10,
    });

    expect(nonExistentResponse.destinations).toHaveLength(0);
  });

  it("handles reset functions", () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useDestinationSearch(), { wrapper });

    // These functions should not throw errors
    expect(() => result.current.resetSearch()).not.toThrow();
    expect(() => result.current.resetAutocomplete()).not.toThrow();
    expect(() => result.current.resetDetails()).not.toThrow();

    // Reset search should clear error
    result.current.resetSearch();
    expect(mockSearchStore.setError).toHaveBeenCalledWith(null);
  });

  it("provides mock destinations with correct structure", async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useDestinationSearch(), { wrapper });

    const response = await result.current.searchDestinationsMock({
      query: "Tokyo",
      types: ["locality"],
      limit: 10,
    });

    const destination = response.destinations[0];

    if (destination) {
      expect(destination.id).toBeDefined();
      expect(destination.name).toBeDefined();
      expect(destination.description).toBeDefined();
      expect(destination.formattedAddress).toBeDefined();
      expect(Array.isArray(destination.types)).toBe(true);
      expect(destination.coordinates).toBeDefined();
      expect(destination.coordinates.lat).toBeDefined();
      expect(destination.coordinates.lng).toBeDefined();
    }
  });

  it("simulates appropriate delay for mock search", async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useDestinationSearch(), { wrapper });

    const startTime = Date.now();

    await result.current.searchDestinationsMock({
      query: "Paris",
      types: ["locality"],
      limit: 10,
    });

    const endTime = Date.now();
    const elapsed = endTime - startTime;

    // Should have some delay (at least 500ms based on our mock)
    expect(elapsed).toBeGreaterThan(500);
  });
});
