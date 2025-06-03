import { useApiMutation, useApiQuery } from "@/hooks/use-api-query";
import { useSearchStore } from "@/stores/search-store";
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { vi } from "vitest";
import { useRecentSearches, useSavedSearches, useSearch } from "../use-search";

// Mock dependencies
vi.mock("@/stores/search-store", () => ({
  useSearchStore: vi.fn(),
}));

vi.mock("@/hooks/use-api-query", () => ({
  useApiQuery: vi.fn(),
  useApiMutation: vi.fn(),
}));

// Mock zustand store implementation
const createMockStore = (initialState: any = {}) => {
  const state = {
    currentSearchType: null,
    currentParams: null,
    flightParams: {},
    accommodationParams: {},
    activityParams: {},
    results: {},
    isLoading: false,
    error: null,
    activeFilters: {},
    activeSortOption: null,
    savedSearches: [],
    recentSearches: [],

    setSearchType: vi.fn(),
    updateFlightParams: vi.fn(),
    updateAccommodationParams: vi.fn(),
    updateActivityParams: vi.fn(),
    resetParams: vi.fn(),
    setResults: vi.fn(),
    setIsLoading: vi.fn(),
    setError: vi.fn(),
    clearResults: vi.fn(),
    setActiveFilter: vi.fn(),
    clearFilters: vi.fn(),
    setActiveSortOption: vi.fn(),
    saveSearch: vi.fn(),
    deleteSearch: vi.fn(),
    addRecentSearch: vi.fn(),
    clearRecentSearches: vi.fn(),
    ...initialState,
  };

  // Mock the computed getter for currentParams
  Object.defineProperty(state, "currentParams", {
    get: function () {
      if (!this.currentSearchType) return null;

      switch (this.currentSearchType) {
        case "flight":
          return this.flightParams;
        case "accommodation":
          return this.accommodationParams;
        case "activity":
          return this.activityParams;
        default:
          return null;
      }
    },
  });

  return state;
};

describe("useSearch hook", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Mock store
    const mockState = createMockStore();
    (useSearchStore as any).mockImplementation(() => mockState);

    // Mock API mutation
    (useApiMutation as any).mockImplementation(() => ({
      mutate: vi.fn(),
      isPending: false,
    }));
  });

  it("exposes store state and actions", () => {
    const { result } = renderHook(() => useSearch());

    expect(result.current.currentSearchType).toBeNull();
    expect(result.current.currentParams).toBeNull();
    expect(result.current.results).toEqual({});
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();

    expect(typeof result.current.setSearchType).toBe("function");
    expect(typeof result.current.updateParams).toBe("function");
    expect(typeof result.current.resetParams).toBe("function");
    expect(typeof result.current.search).toBe("function");
    expect(typeof result.current.setActiveFilter).toBe("function");
    expect(typeof result.current.clearFilters).toBe("function");
    expect(typeof result.current.setActiveSortOption).toBe("function");
  });

  it("updates parameters based on search type", () => {
    const mockStore = createMockStore({
      currentSearchType: "flight",
    });
    (useSearchStore as any).mockImplementation(() => mockStore);

    const { result } = renderHook(() => useSearch());

    act(() => {
      result.current.updateParams({ origin: "NYC", destination: "LAX" });
    });

    expect(mockStore.updateFlightParams).toHaveBeenCalledWith({
      origin: "NYC",
      destination: "LAX",
    });
  });

  it("performs a search with correct parameters", () => {
    const searchMutateMock = vi.fn();
    (useApiMutation as any).mockImplementation(() => ({
      mutate: searchMutateMock,
      isPending: false,
    }));

    const mockStore = createMockStore({
      currentSearchType: "flight",
      flightParams: {
        origin: "NYC",
        destination: "LAX",
        startDate: "2025-06-01",
        endDate: "2025-06-08",
      },
      activeFilters: { airline: ["test-airlines"] },
      activeSortOption: { value: "price", direction: "asc" },
    });
    (useSearchStore as any).mockImplementation(() => mockStore);

    const { result } = renderHook(() => useSearch());

    act(() => {
      result.current.search();
    });

    expect(mockStore.setIsLoading).toHaveBeenCalledWith(true);
    expect(mockStore.clearResults).toHaveBeenCalled();
    expect(searchMutateMock).toHaveBeenCalledWith({
      type: "flight",
      params: {
        origin: "NYC",
        destination: "LAX",
        startDate: "2025-06-01",
        endDate: "2025-06-08",
        filters: { airline: ["test-airlines"] },
        sort: "price",
        sortDirection: "asc",
      },
    });
  });

  it("updates loading state based on mutation state", () => {
    (useApiMutation as any).mockImplementation(() => ({
      mutate: vi.fn(),
      isPending: true,
    }));

    const mockStore = createMockStore({ isLoading: false });
    (useSearchStore as any).mockImplementation(() => mockStore);

    const { result } = renderHook(() => useSearch());

    expect(result.current.isLoading).toBe(true);
  });

  it("handles search error when parameters not set", () => {
    const mockStore = createMockStore({
      currentSearchType: null,
      setError: vi.fn(),
    });
    (useSearchStore as any).mockImplementation(() => mockStore);

    const { result } = renderHook(() => useSearch());

    act(() => {
      result.current.search();
    });

    expect(mockStore.setError).toHaveBeenCalledWith(
      "Search type or parameters not set"
    );
  });
});

describe("useSavedSearches hook", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Mock store
    const mockState = createMockStore({
      savedSearches: [
        {
          id: "saved-1",
          name: "NYC to LAX",
          type: "flight",
          params: { origin: "NYC", destination: "LAX" },
          createdAt: "2025-01-01T00:00:00Z",
        },
      ],
    });
    (useSearchStore as any).mockImplementation(() => mockState);

    // Mock API query and mutation
    (useApiQuery as any).mockImplementation(() => ({
      data: { searches: [] },
      isLoading: false,
      refetch: vi.fn(),
    }));

    (useApiMutation as any).mockImplementation(() => ({
      mutate: vi.fn(),
      isPending: false,
    }));
  });

  it("provides local saved searches", () => {
    const { result } = renderHook(() => useSavedSearches());

    expect(result.current.savedSearches).toHaveLength(1);
    expect(result.current.savedSearches[0].name).toBe("NYC to LAX");
  });

  it("loads a saved search correctly", () => {
    const mockStore = createMockStore({
      savedSearches: [
        {
          id: "saved-1",
          name: "NYC to LAX",
          type: "flight",
          params: { origin: "NYC", destination: "LAX" },
          createdAt: "2025-01-01T00:00:00Z",
        },
      ],
    });

    const mockGetState = vi.fn(() => ({
      setSearchType: vi.fn(),
      updateFlightParams: vi.fn(),
      updateAccommodationParams: vi.fn(),
      updateActivityParams: vi.fn(),
    }));

    (useSearchStore as any).mockImplementation(() => mockStore);
    (useSearchStore.getState as any) = mockGetState;

    const { result } = renderHook(() => useSavedSearches());

    act(() => {
      result.current.loadSavedSearch(mockStore.savedSearches[0]);
    });

    expect(mockGetState).toHaveBeenCalled();
  });

  it("enables remote operations for saved searches", () => {
    const refetchMock = vi.fn();

    (useApiQuery as any).mockImplementation(() => ({
      data: {
        searches: [
          {
            id: "remote-1",
            name: "Remote Search",
            type: "accommodation",
            params: { destination: "Paris" },
            createdAt: "2025-01-02T00:00:00Z",
          },
        ],
      },
      isLoading: false,
      refetch: refetchMock,
    }));

    const { result } = renderHook(() => useSavedSearches());

    expect(result.current.remoteSavedSearches).toHaveLength(1);
    expect(result.current.remoteSavedSearches[0].name).toBe("Remote Search");

    act(() => {
      result.current.refreshSavedSearches();
    });

    expect(refetchMock).toHaveBeenCalled();
  });
});

describe("useRecentSearches hook", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Mock store
    const mockState = createMockStore({
      recentSearches: [
        {
          type: "flight",
          params: { origin: "NYC", destination: "LAX" },
          timestamp: "2025-01-01T00:00:00Z",
        },
      ],
      clearRecentSearches: vi.fn(),
    });
    (useSearchStore as any).mockImplementation(() => mockState);
  });

  it("provides recent searches", () => {
    const { result } = renderHook(() => useRecentSearches());

    expect(result.current.recentSearches).toHaveLength(1);
    expect(result.current.recentSearches[0].params.origin).toBe("NYC");
  });

  it("loads a recent search correctly", () => {
    const mockGetState = vi.fn(() => ({
      setSearchType: vi.fn(),
      updateFlightParams: vi.fn(),
      updateAccommodationParams: vi.fn(),
      updateActivityParams: vi.fn(),
    }));

    (useSearchStore.getState as any) = mockGetState;

    const { result } = renderHook(() => useRecentSearches());

    act(() => {
      result.current.loadRecentSearch("flight", {
        origin: "NYC",
        destination: "LAX",
      });
    });

    expect(mockGetState).toHaveBeenCalled();
  });

  it("clears recent searches", () => {
    const mockStore = createMockStore({
      recentSearches: [
        {
          type: "flight",
          params: { origin: "NYC", destination: "LAX" },
          timestamp: "2025-01-01T00:00:00Z",
        },
      ],
      clearRecentSearches: vi.fn(),
    });
    (useSearchStore as any).mockImplementation(() => mockStore);

    const { result } = renderHook(() => useRecentSearches());

    act(() => {
      result.current.clearRecentSearches();
    });

    expect(mockStore.clearRecentSearches).toHaveBeenCalled();
  });
});
