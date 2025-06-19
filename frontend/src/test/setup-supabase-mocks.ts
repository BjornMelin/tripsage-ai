import { vi } from "vitest";
import { createMockSupabaseClient } from "./mock-helpers";

// Mock environment variables
vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://test.supabase.co");
vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "test-anon-key");

// Create a function that returns a new mock client instance each time
// This ensures tests don't interfere with each other
const getMockSupabaseClient = () => createMockSupabaseClient();

// Mock @supabase/ssr module
vi.mock("@supabase/ssr", () => ({
  createBrowserClient: vi.fn(() => getMockSupabaseClient()),
  createServerClient: vi.fn(() => getMockSupabaseClient()),
}));

// Mock the Supabase client module
vi.mock("@/lib/supabase/client", () => ({
  createClient: vi.fn(() => getMockSupabaseClient()),
  useSupabase: vi.fn(() => getMockSupabaseClient()),
}));

// Also mock dynamic imports of the Supabase client
vi.doMock("@/lib/supabase/client", () => ({
  createClient: vi.fn(() => getMockSupabaseClient()),
  useSupabase: vi.fn(() => getMockSupabaseClient()),
}));

// Mock the useAuth hook
vi.mock("@/contexts/auth-context", () => ({
  useAuth: vi.fn(() => ({
    user: { id: "test-user-id", email: "test@example.com" },
    session: {
      access_token: "test-token",
      refresh_token: "test-refresh-token",
      expires_at: Date.now() + 3600000,
      user: { id: "test-user-id", email: "test@example.com" },
    },
    isLoading: false,
    error: null,
    signIn: vi.fn().mockResolvedValue({ error: null }),
    signUp: vi.fn().mockResolvedValue({ error: null }),
    signOut: vi.fn().mockResolvedValue(undefined),
    resetPassword: vi.fn().mockResolvedValue({ error: null }),
  })),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}));

// Mock fetch globally with better error handling
global.fetch = vi.fn().mockImplementation((url: string) => {
  // Default to successful response
  return Promise.resolve({
    ok: true,
    status: 200,
    json: async () => ({ data: null, error: null }),
    text: async () => "",
    headers: new Headers(),
  });
});

// Mock hooks that depend on Supabase
vi.mock("@/hooks/use-trips-supabase", () => ({
  useAllTrips: vi.fn(() => ({
    data: [],
    error: null,
    isLoading: false,
    refetch: vi.fn(),
  })),
  useTripData: vi.fn(() => ({
    data: null,
    error: null,
    isLoading: false,
    refetch: vi.fn(),
  })),
}));

vi.mock("@/hooks/use-trips", () => ({
  useUpcomingFlights: vi.fn(() => ({
    data: [],
    error: null,
    isLoading: false,
    isError: false,
    isPending: false,
    isSuccess: true,
    refetch: vi.fn(),
  })),
  useGetTrip: vi.fn(() => ({
    data: null,
    error: null,
    isLoading: false,
    isError: false,
    isPending: false,
    isSuccess: false,
    refetch: vi.fn(),
  })),
  useCreateTrip: vi.fn(() => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    isPending: false,
    isError: false,
    isSuccess: false,
    error: null,
    data: null,
  })),
  useUpdateTrip: vi.fn(() => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    isPending: false,
    isError: false,
    isSuccess: false,
    error: null,
    data: null,
  })),
  useDeleteTrip: vi.fn(() => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    isPending: false,
    isError: false,
    isSuccess: false,
    error: null,
    data: null,
  })),
}));

vi.mock("@/hooks/use-supabase-realtime", () => ({
  useSupabaseRealtime: vi.fn(() => ({
    connectionStatus: "connected",
    error: null,
    disconnect: vi.fn(),
    reconnect: vi.fn(),
  })),
  useTripRealtime: vi.fn(() => ({
    connectionStatus: { trips: "connected", destinations: "connected" },
    error: null,
  })),
  useChatRealtime: vi.fn(() => ({
    connectionStatus: "connected",
    error: null,
    newMessageCount: 0,
    clearMessageCount: vi.fn(),
  })),
  useRealtimeStatus: vi.fn(() => ({
    trips: { status: "connected", error: null },
    destinations: { status: "connected", error: null },
    chat: { status: "connected", error: null },
  })),
}));

// Mock search-store and its re-exports
vi.mock("@/stores/search-store", () => ({
  useSearchStore: vi.fn(() => ({
    currentSearchType: "flight",
    currentParams: { origin: "NYC", destination: "LAX" },
    hasActiveFilters: true,
    hasResults: true,
    isSearching: true,
    initializeSearch: vi.fn().mockImplementation((type) => {
      // Update internal state simulation
      return type;
    }),
    executeSearch: vi.fn().mockResolvedValue("search-123"),
    resetSearch: vi.fn(),
    loadSavedSearch: vi.fn().mockResolvedValue(true),
    duplicateCurrentSearch: vi.fn().mockResolvedValue("new-saved-123"),
    validateAndExecuteSearch: vi.fn().mockResolvedValue(null),
    applyFiltersAndSearch: vi.fn().mockResolvedValue("filtered-search-123"),
    retryLastSearch: vi.fn().mockResolvedValue("new-search-id"),
    syncStores: vi.fn(),
    getSearchSummary: vi.fn(() => ({
      searchType: "flight",
      params: { origin: "NYC", destination: "LAX" },
      hasResults: true,
      resultCount: 10,
      isSearching: true,
      hasActiveFilters: true,
    })),
  })),
  useSearchParamsStore: vi.fn(() => ({
    currentSearchType: "flight",
    currentParams: { origin: "NYC", destination: "LAX" },
    paramsValidation: {
      flight: true,
      accommodation: true,
      activity: true,
      destination: true,
    },
    isValidating: {
      flight: false,
      accommodation: false,
      activity: false,
      destination: false,
    },
    setSearchType: vi.fn().mockImplementation((type) => {
      // Mock implementation that updates internal state
      return { setSearchType: vi.fn() };
    }),
    updateFlightParams: vi.fn(),
    updateAccommodationParams: vi.fn(),
    updateActivityParams: vi.fn(),
    updateDestinationParams: vi.fn(),
    validateCurrentParams: vi.fn(() => Promise.resolve(false)),
    clearParams: vi.fn(),
    reset: vi.fn(),
    loadParamsFromTemplate: vi.fn(),
  })),
  useSearchResultsStore: vi.fn(() => ({
    results: {},
    hasResults: false,
    isSearching: false,
    status: "idle",
    error: null,
    currentSearchId: null,
    searchProgress: 0,
    setSearchResults: vi.fn(),
    startSearch: vi.fn(() => "search-id"),
    clearResults: vi.fn(),
    setSearchError: vi.fn(),
    updateSearchProgress: vi.fn(),
    completeSearch: vi.fn(),
    cancelSearch: vi.fn(),
    getAverageSearchDuration: vi.fn(() => 0),
    getSearchSuccessRate: vi.fn(() => 0),
  })),
  useSearchFiltersStore: vi.fn(() => ({
    searchType: null,
    activeFilters: {},
    availableFilters: {},
    activeSort: null,
    activeSortDirection: "asc",
    filterPresets: {},
    activePreset: null,
    setSearchType: vi.fn(),
    setActiveFilter: vi.fn(),
    clearFilters: vi.fn(),
    reset: vi.fn(),
    softReset: vi.fn(),
    setAvailableFilters: vi.fn(),
    setSortOptions: vi.fn(),
    setSortById: vi.fn(),
    toggleSortDirection: vi.fn(),
  })),
  useSearchHistoryStore: vi.fn(() => ({
    recentSearches: [],
    savedSearches: [],
    favoriteSearches: [],
    searchAnalytics: {},
    addRecentSearch: vi.fn(),
    saveSearch: vi.fn(() => Promise.resolve("saved-search-id")),
    clearHistory: vi.fn(),
    removeRecentSearch: vi.fn(),
    markSearchAsUsed: vi.fn(),
  })),
  // Re-export utility hooks
  useSearchType: vi.fn(() => null),
  useCurrentSearchParams: vi.fn(() => null),
  useSearchParamsValidation: vi.fn(() => ({})),
  useSearchStatus: vi.fn(() => "idle"),
  useSearchResults: vi.fn(() => ({})),
  useIsSearching: vi.fn(() => false),
  useSearchProgress: vi.fn(() => 0),
  useSearchError: vi.fn(() => null),
  useHasSearchResults: vi.fn(() => false),
  useActiveFilters: vi.fn(() => ({})),
  useActiveSortOption: vi.fn(() => null),
  useCurrentFilters: vi.fn(() => ({ filters: {}, sort: null })),
  useHasActiveFilters: vi.fn(() => false),
  useFilterPresets: vi.fn(() => ({})),
  useRecentSearches: vi.fn(() => []),
  useSavedSearches: vi.fn(() => []),
  useFavoriteSearches: vi.fn(() => []),
  useSearchSuggestions: vi.fn(() => []),
  useSearchAnalytics: vi.fn(() => ({})),
}));

// Mock API key store
vi.mock("@/stores/api-key-store", () => ({
  useApiKeyStore: vi.fn(() => ({
    keys: {},
    supportedServices: ["google-maps", "openai", "weather"],
    selectedService: null,
    isLoading: false,
    error: null,
    setKeys: vi.fn(),
    setSelectedService: vi.fn(),
    setLoading: vi.fn(),
    setError: vi.fn(),
    clearError: vi.fn(),
    reset: vi.fn(),
  })),
}));

// Mock user store
vi.mock("@/stores/user-store", () => ({
  useUserProfileStore: vi.fn(() => ({
    profile: {
      id: "test-user-id",
      email: "test@example.com",
      name: "Test User",
      twoFactorEnabled: false,
      settings: {
        notifications: true,
        privacy: "public",
      },
    },
    preferences: {
      theme: "light",
      language: "en",
    },
    insights: null,
    isLoading: false,
    error: null,
    updateProfile: vi.fn(),
    updatePreferences: vi.fn(),
    refreshInsights: vi.fn(),
    clearError: vi.fn(),
  })),
}));

// Export a function to get mock client for tests that need direct access
export { getMockSupabaseClient };
