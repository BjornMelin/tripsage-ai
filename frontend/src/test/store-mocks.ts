/**
 * Store mock utilities for hook tests
 */
import type { Mock } from "vitest";
import { vi } from "vitest";

// Create mock store with common actions
export const createMockStore = <T extends Record<string, unknown>>(
  initialState: Partial<T> = {}
) => {
  const state = { ...initialState };
  const subscribers = new Set<(state: T) => void>();

  const setState = (updater: Partial<T> | ((prev: T) => Partial<T>)) => {
    const updates = typeof updater === "function" ? updater(state as T) : updater;
    Object.assign(state, updates);
    subscribers.forEach((fn) => fn(state as T));
  };

  const getState = () => state as T;

  const subscribe = (fn: (state: T) => void) => {
    subscribers.add(fn);
    return () => subscribers.delete(fn);
  };

  return {
    getState,
    setState,
    subscribe,
    ...state,
  };
};

// Mock search params store
export interface MockSearchParamsStore {
  updateAccommodationParams: Mock;
  updateFlightParams: Mock;
  updateActivityParams: Mock;
  updateDestinationParams: Mock;
  setSearchType: Mock;
  clearParams: Mock;
}

export const createMockSearchParamsStore = (): MockSearchParamsStore => ({
  updateAccommodationParams: vi.fn(),
  updateFlightParams: vi.fn(),
  updateActivityParams: vi.fn(),
  updateDestinationParams: vi.fn(),
  setSearchType: vi.fn(),
  clearParams: vi.fn(),
});

// Mock search results store
export interface MockSearchResultsStore {
  startSearch: Mock;
  setSearchResults: Mock;
  setSearchError: Mock;
  completeSearch: Mock;
  updateSearchProgress: Mock;
  clearResults: Mock;
  clearAllResults: Mock;
  appendResults: Mock;
  cancelSearch: Mock;
  setIsLoading: Mock;
  setError: Mock;
  setResults: Mock;
}

export const createMockSearchResultsStore = (): MockSearchResultsStore => {
  const store = {
    startSearch: vi.fn((searchType: string, params: Record<string, unknown>) => {
      const searchId = `search_${Date.now()}_test`;
      return searchId;
    }),
    setSearchResults: vi.fn(),
    setSearchError: vi.fn(),
    completeSearch: vi.fn(),
    updateSearchProgress: vi.fn(),
    clearResults: vi.fn(),
    clearAllResults: vi.fn(),
    appendResults: vi.fn(),
    cancelSearch: vi.fn(),
    // Legacy methods for backward compatibility
    setIsLoading: vi.fn(),
    setError: vi.fn(),
    setResults: vi.fn(),
  };

  return store;
};

// Mock search store (combined)
export interface MockSearchStore {
  updateAccommodationParams: Mock;
  updateFlightParams: Mock;
  updateActivityParams: Mock;
  updateDestinationParams: Mock;
  setSearchType: Mock;
  clearParams: Mock;
  startSearch: Mock;
  setSearchResults: Mock;
  setSearchError: Mock;
  completeSearch: Mock;
  setIsLoading: Mock;
  setError: Mock;
  setResults: Mock;
  searchType: string;
  isLoading: boolean;
  error: string | null;
  results: Record<string, unknown>;
}

export const createMockSearchStore = (
  overrides?: Partial<MockSearchStore>
): MockSearchStore => ({
  // Params store methods
  updateAccommodationParams: vi.fn(),
  updateFlightParams: vi.fn(),
  updateActivityParams: vi.fn(),
  updateDestinationParams: vi.fn(),
  setSearchType: vi.fn(),
  clearParams: vi.fn(),
  // Results store methods
  startSearch: vi.fn(() => `search_${Date.now()}_test`),
  setSearchResults: vi.fn(),
  setSearchError: vi.fn(),
  completeSearch: vi.fn(),
  setIsLoading: vi.fn(),
  setError: vi.fn(),
  setResults: vi.fn(),
  // State
  searchType: "accommodation",
  isLoading: false,
  error: null,
  results: {},
  ...overrides,
});

// Mock budget store
export interface MockBudgetStore {
  selectedBudgetId: string | null;
  budgets: Array<{ id: string; name: string; amount: number }>;
  expenses: Array<{ id: string; budgetId: string; amount: number }>;
  alerts: Array<{ id: string; budgetId: string; type: string }>;
  isLoading: boolean;
  error: string | null;
  selectBudget: Mock;
  addBudget: Mock;
  updateBudget: Mock;
  deleteBudget: Mock;
  addExpense: Mock;
  updateExpense: Mock;
  deleteExpense: Mock;
  addAlert: Mock;
  updateAlert: Mock;
  deleteAlert: Mock;
  loadBudgets: Mock;
  clearError: Mock;
}

export const createMockBudgetStore = (
  overrides?: Partial<MockBudgetStore>
): MockBudgetStore => ({
  selectedBudgetId: null,
  budgets: [],
  expenses: [],
  alerts: [],
  isLoading: false,
  error: null,
  selectBudget: vi.fn(),
  addBudget: vi.fn(),
  updateBudget: vi.fn(),
  deleteBudget: vi.fn(),
  addExpense: vi.fn(),
  updateExpense: vi.fn(),
  deleteExpense: vi.fn(),
  addAlert: vi.fn(),
  updateAlert: vi.fn(),
  deleteAlert: vi.fn(),
  loadBudgets: vi.fn(),
  clearError: vi.fn(),
  ...overrides,
});

// Mock deals store
export interface MockDealsStore {
  deals: Array<{
    id: string;
    title: string;
    type: string;
    destination: string;
    isFeatured: boolean;
    isSaved: boolean;
  }>;
  filters: {
    type: string | null;
    destination: string | null;
  };
  isLoading: boolean;
  error: string | null;
  filteredDeals: Array<unknown>;
  featuredDeals: Array<unknown>;
  savedDeals: Array<unknown>;
  toggleFeatured: Mock;
  toggleSaved: Mock;
  setTypeFilter: Mock;
  setDestinationFilter: Mock;
  clearFilters: Mock;
  loadDeals: Mock;
}

export const createMockDealsStore = (
  overrides?: Partial<MockDealsStore>
): MockDealsStore => ({
  deals: [],
  filters: {
    type: null,
    destination: null,
  },
  isLoading: false,
  error: null,
  filteredDeals: [],
  featuredDeals: [],
  savedDeals: [],
  toggleFeatured: vi.fn(),
  toggleSaved: vi.fn(),
  setTypeFilter: vi.fn(),
  setDestinationFilter: vi.fn(),
  clearFilters: vi.fn(),
  loadDeals: vi.fn(),
  ...overrides,
});

// Mock search history store
export interface MockSearchHistoryStore {
  recentSearches: Array<{
    id: string;
    query: string;
    timestamp: string;
    type: string;
  }>;
  savedSearches: Array<{
    id: string;
    query: string;
    timestamp: string;
    type: string;
  }>;
  addRecentSearch: Mock;
  clearRecentSearches: Mock;
  loadRecentSearch: Mock;
  saveSearch: Mock;
  removeSavedSearch: Mock;
  loadSavedSearch: Mock;
  syncSavedSearches: Mock;
}

export const createMockSearchHistoryStore = (
  overrides?: Partial<MockSearchHistoryStore>
): MockSearchHistoryStore => ({
  recentSearches: [],
  savedSearches: [],
  addRecentSearch: vi.fn(),
  clearRecentSearches: vi.fn(),
  loadRecentSearch: vi.fn(),
  saveSearch: vi.fn(),
  removeSavedSearch: vi.fn(),
  loadSavedSearch: vi.fn(),
  syncSavedSearches: vi.fn(),
  ...overrides,
});

// Mock user store
export interface MockUserStore {
  user: {
    id: string;
    email: string;
    name: string;
  } | null;
  preferences: Record<string, unknown>;
  isLoading: boolean;
  error: string | null;
  updateUser: Mock;
  updatePreferences: Mock;
  clearUser: Mock;
}

export const createMockUserStore = (
  overrides?: Partial<MockUserStore>
): MockUserStore => ({
  user: null,
  preferences: {},
  isLoading: false,
  error: null,
  updateUser: vi.fn(),
  updatePreferences: vi.fn(),
  clearUser: vi.fn(),
  ...overrides,
});

// Mock auth store
export interface MockAuthStore {
  isAuthenticated: boolean;
  user: {
    id: string;
    email: string;
    name: string;
  } | null;
  session: unknown | null;
  isLoading: boolean;
  error: string | null;
  signIn: Mock;
  signUp: Mock;
  signOut: Mock;
  refreshSession: Mock;
  clearError: Mock;
}

export const createMockAuthStore = (
  overrides?: Partial<MockAuthStore>
): MockAuthStore => ({
  isAuthenticated: false,
  user: null,
  session: null,
  isLoading: false,
  error: null,
  signIn: vi.fn(),
  signUp: vi.fn(),
  signOut: vi.fn(),
  refreshSession: vi.fn(),
  clearError: vi.fn(),
  ...overrides,
});

// Mock agent status store
export interface MockAgentStatusStore {
  agents: Record<string, { id: string; status: string; lastUpdate: string }>;
  connectionStatus: string;
  isConnected: boolean;
  updateAgentStatus: Mock;
  removeAgent: Mock;
  setConnectionStatus: Mock;
  clearAgents: Mock;
}

export const createMockAgentStatusStore = (
  overrides?: Partial<MockAgentStatusStore>
): MockAgentStatusStore => ({
  agents: {},
  connectionStatus: "disconnected",
  isConnected: false,
  updateAgentStatus: vi.fn(),
  removeAgent: vi.fn(),
  setConnectionStatus: vi.fn(),
  clearAgents: vi.fn(),
  ...overrides,
});

// Mock chat store
export interface MockChatStore {
  messages: Array<{ id: string; content: string; role: string }>;
  sessions: Array<{ id: string; title: string }>;
  activeSessionId: string | null;
  isLoading: boolean;
  error: string | null;
  addMessage: Mock;
  updateMessage: Mock;
  deleteMessage: Mock;
  createSession: Mock;
  selectSession: Mock;
  deleteSession: Mock;
  clearMessages: Mock;
}

export const createMockChatStore = (
  overrides?: Partial<MockChatStore>
): MockChatStore => ({
  messages: [],
  sessions: [],
  activeSessionId: null,
  isLoading: false,
  error: null,
  addMessage: vi.fn(),
  updateMessage: vi.fn(),
  deleteMessage: vi.fn(),
  createSession: vi.fn(),
  selectSession: vi.fn(),
  deleteSession: vi.fn(),
  clearMessages: vi.fn(),
  ...overrides,
});

// Mock trip store
export interface MockTripStore {
  trips: Array<{ id: string; title: string; destination: string }>;
  selectedTripId: string | null;
  isLoading: boolean;
  error: string | null;
  createTrip: Mock;
  updateTrip: Mock;
  deleteTrip: Mock;
  selectTrip: Mock;
  loadTrips: Mock;
  clearError: Mock;
}

export const createMockTripStore = (
  overrides?: Partial<MockTripStore>
): MockTripStore => ({
  trips: [],
  selectedTripId: null,
  isLoading: false,
  error: null,
  createTrip: vi.fn(),
  updateTrip: vi.fn(),
  deleteTrip: vi.fn(),
  selectTrip: vi.fn(),
  loadTrips: vi.fn(),
  clearError: vi.fn(),
  ...overrides,
});

// Mock currency store
export interface MockCurrencyStore {
  baseCurrency: string;
  targetCurrencies: string[];
  exchangeRates: Record<string, number>;
  isLoading: boolean;
  error: string | null;
  setBaseCurrency: Mock;
  addTargetCurrency: Mock;
  removeTargetCurrency: Mock;
  updateExchangeRates: Mock;
  convert: Mock;
}

export const createMockCurrencyStore = (
  overrides?: Partial<MockCurrencyStore>
): MockCurrencyStore => ({
  baseCurrency: "USD",
  targetCurrencies: ["EUR", "GBP"],
  exchangeRates: { EUR: 0.85, GBP: 0.73 },
  isLoading: false,
  error: null,
  setBaseCurrency: vi.fn(),
  addTargetCurrency: vi.fn(),
  removeTargetCurrency: vi.fn(),
  updateExchangeRates: vi.fn(),
  convert: vi.fn((amount: number, from: string, to: string) => {
    if (from === to) return amount;
    return amount * 0.85; // Mock conversion
  }),
  ...overrides,
});

// Helper to mock multiple stores at once
export const mockStores = (stores: {
  searchParams?: Partial<MockSearchParamsStore>;
  searchResults?: Partial<MockSearchResultsStore>;
  search?: Partial<MockSearchStore>;
  budget?: Partial<MockBudgetStore>;
  deals?: Partial<MockDealsStore>;
  searchHistory?: Partial<MockSearchHistoryStore>;
  user?: Partial<MockUserStore>;
  auth?: Partial<MockAuthStore>;
  agentStatus?: Partial<MockAgentStatusStore>;
  chat?: Partial<MockChatStore>;
  trip?: Partial<MockTripStore>;
  currency?: Partial<MockCurrencyStore>;
}) => {
  const mocks: Record<string, unknown> = {};

  if (stores.searchParams) {
    mocks.searchParams = createMockSearchParamsStore();
    Object.assign(mocks.searchParams, stores.searchParams);
  }

  if (stores.searchResults) {
    mocks.searchResults = createMockSearchResultsStore();
    Object.assign(mocks.searchResults, stores.searchResults);
  }

  if (stores.search) {
    mocks.search = createMockSearchStore(stores.search);
  }

  if (stores.budget) {
    mocks.budget = createMockBudgetStore(stores.budget);
  }

  if (stores.deals) {
    mocks.deals = createMockDealsStore(stores.deals);
  }

  if (stores.searchHistory) {
    mocks.searchHistory = createMockSearchHistoryStore(stores.searchHistory);
  }

  if (stores.user) {
    mocks.user = createMockUserStore(stores.user);
  }

  if (stores.auth) {
    mocks.auth = createMockAuthStore(stores.auth);
  }

  if (stores.agentStatus) {
    mocks.agentStatus = createMockAgentStatusStore(stores.agentStatus);
  }

  if (stores.chat) {
    mocks.chat = createMockChatStore(stores.chat);
  }

  if (stores.trip) {
    mocks.trip = createMockTripStore(stores.trip);
  }

  if (stores.currency) {
    mocks.currency = createMockCurrencyStore(stores.currency);
  }

  return mocks;
};
