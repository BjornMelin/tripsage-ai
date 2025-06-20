import type { SupabaseClient } from "@supabase/supabase-js";
import type { UseQueryResult } from "@tanstack/react-query";
/**
 * Comprehensive mock helpers for TypeScript compliance
 */
import { vi } from "vitest";

// Complete Supabase Query Builder Mock
export const createCompleteQueryBuilder = (
  mockData: unknown = null,
  mockError: unknown = null
) => {
  const builder = {
    select: vi.fn().mockReturnThis(),
    insert: vi.fn().mockReturnThis(),
    update: vi.fn().mockReturnThis(),
    delete: vi.fn().mockReturnThis(),
    eq: vi.fn().mockReturnThis(),
    order: vi.fn().mockReturnThis(),
    range: vi.fn().mockReturnThis(),
    single: vi.fn().mockResolvedValue({ data: mockData, error: mockError }),
    maybeSingle: vi.fn().mockResolvedValue({ data: mockData, error: mockError }),
  };

  // Make the builder itself a thenable for direct await
  (builder as any).then = (onFulfilled: any) => {
    return Promise.resolve({ data: mockData, error: mockError }).then(onFulfilled);
  };

  return builder;
};

// Helper to generate trip data
const generateTripData = (data: any) => {
  const id = Date.now();
  const now = new Date().toISOString();
  return {
    id,
    uuid_id: `uuid-${id}`,
    user_id: "test-user-id",
    title: data.title || data.name || "Untitled Trip",
    name: data.title || data.name || "Untitled Trip",
    description: data.description || "",
    start_date: data.startDate || data.start_date || null,
    end_date: data.endDate || data.end_date || null,
    destination: data.destination || null,
    budget: data.budget || null,
    currency: data.currency || "USD",
    spent_amount: data.spent_amount || 0,
    visibility: data.visibility || "private",
    tags: data.tags || [],
    preferences: data.preferences || {},
    status: data.status || "planning",
    budget_breakdown: data.enhanced_budget || null,
    created_at: now,
    updated_at: now,
  };
};

// Complete SupabaseAuthClient Mock
export const createMockSupabaseAuthClient = (): Partial<SupabaseClient["auth"]> => {
  return {
    getSession: vi.fn().mockResolvedValue({ data: { session: null }, error: null }),
    onAuthStateChange: vi.fn().mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } },
    }),
    signUp: vi.fn().mockResolvedValue({ data: null, error: null }),
    signInWithPassword: vi.fn().mockResolvedValue({ data: null, error: null }),
    signOut: vi.fn().mockResolvedValue({ error: null }),
    resend: vi.fn().mockResolvedValue({ data: null, error: null }),
    updateUser: vi.fn().mockResolvedValue({ data: null, error: null }),
    getUser: vi.fn().mockResolvedValue({ data: { user: null }, error: null }),
    verifyOtp: vi.fn().mockResolvedValue({ data: null, error: null }),
    signInWithOAuth: vi
      .fn()
      .mockResolvedValue({ data: { url: "", provider: "github" }, error: null }),
    signInWithOtp: vi.fn().mockResolvedValue({ data: null, error: null }),
    signInWithIdToken: vi.fn().mockResolvedValue({ data: null, error: null }),
    signInWithSSO: vi.fn().mockResolvedValue({ data: null, error: null }),
    signInAnonymously: vi.fn().mockResolvedValue({ data: null, error: null }),
    signInWithWeb3: vi.fn().mockResolvedValue({ data: null, error: null }),
    exchangeCodeForSession: vi.fn().mockResolvedValue({ data: null, error: null }),
    reauthenticate: vi.fn().mockResolvedValue({ data: null, error: null }),
    linkIdentity: vi
      .fn()
      .mockResolvedValue({ data: { url: "", provider: "github" }, error: null }),
    unlinkIdentity: vi.fn().mockResolvedValue({ data: null, error: null }),
    getUserIdentities: vi
      .fn()
      .mockResolvedValue({ data: { identities: [] }, error: null }),
    setSession: vi.fn().mockResolvedValue({ data: null, error: null }),
    refreshSession: vi.fn().mockResolvedValue({ data: null, error: null }),
    initialize: vi.fn().mockResolvedValue({ error: null }),
  } as Partial<SupabaseClient["auth"]>;
};

// Complete Supabase Client Mock
export const createMockSupabaseClient = (): Partial<SupabaseClient> => {
  const mockData: Record<string, any[]> = {
    trips: [],
  };

  return {
    auth: createMockSupabaseAuthClient() as any,
    from: vi.fn((table: string) => {
      const builder: any = {
        select: vi.fn().mockReturnThis(),
        insert: vi
          .fn((data: any[]) => {
            // Handle insert operations
            const insertedData = data.map((item) => generateTripData(item));
            mockData[table] = [...mockData[table], ...insertedData];
            builder._insertedData = insertedData;
            return builder;
          })
          .mockReturnThis(),
        update: vi.fn().mockReturnThis(),
        delete: vi.fn().mockReturnThis(),
        eq: vi.fn().mockReturnThis(),
        order: vi.fn().mockReturnThis(),
        range: vi.fn().mockReturnThis(),
        single: vi.fn().mockImplementation(() => {
          if (builder._insertedData && builder._insertedData.length === 1) {
            return Promise.resolve({ data: builder._insertedData[0], error: null });
          }
          return Promise.resolve({ data: mockData[table]?.[0] || null, error: null });
        }),
        maybeSingle: vi
          .fn()
          .mockResolvedValue({ data: mockData[table]?.[0] || null, error: null }),
      };

      // Make the builder itself a thenable
      builder.then = (onFulfilled: any) => {
        return Promise.resolve({ data: mockData[table] || [], error: null }).then(
          onFulfilled
        );
      };

      return builder;
    }),
    channel: vi.fn().mockReturnValue({
      on: vi.fn().mockReturnThis(),
      subscribe: vi.fn().mockReturnValue({
        unsubscribe: vi.fn(),
      }),
    }),
    removeChannel: vi.fn(),
  };
};

// Complete UseQueryResult Mock
export const createMockUseQueryResult = <T, E = Error>(
  data: T | null = null,
  error: E | null = null,
  isLoading = false,
  isError = false
): UseQueryResult<T, E> =>
  ({
    data,
    error,
    isLoading,
    isError,
    isSuccess: !isLoading && !isError && data !== null,
    isPending: isLoading,
    isFetching: false,
    isFetched: !isLoading,
    isFetchedAfterMount: !isLoading,
    isRefetching: false,
    isLoadingError: false,
    isRefetchError: false,
    isPlaceholderData: false,
    isPaused: false,
    isStale: false,
    dataUpdatedAt: Date.now(),
    errorUpdatedAt: error ? Date.now() : 0,
    failureCount: error ? 1 : 0,
    failureReason: error,
    errorUpdateCount: error ? 1 : 0,
    status: isLoading ? "pending" : isError ? "error" : "success",
    fetchStatus: "idle",
    refetch: vi.fn().mockResolvedValue({ data, error }),
    isInitialLoading: isLoading,
    promise: Promise.resolve(data as T),
  }) as UseQueryResult<T, E>;

// Enhanced error mock - matches the real ApiError interface
export class MockApiError extends Error {
  public readonly status: number;
  public readonly code?: string;
  public readonly details?: Record<string, unknown>;
  public readonly timestamp: string;
  public readonly path?: string;

  constructor(
    message: string,
    status = 500,
    code?: string,
    details?: Record<string, unknown>
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.timestamp = new Date().toISOString();
    Object.setPrototypeOf(this, MockApiError.prototype);
  }

  get isClientError(): boolean {
    return this.status >= 400 && this.status < 500;
  }

  get isServerError(): boolean {
    return this.status >= 500;
  }

  get shouldRetry(): boolean {
    return this.isServerError || this.status === 408 || this.status === 429;
  }

  get userMessage(): string {
    if (this.status === 401) return "Authentication required. Please log in.";
    if (this.status === 403) return "You don't have permission to perform this action.";
    if (this.status === 404) return "The requested resource was not found.";
    if (this.status === 422) return "Invalid data provided. Please check your input.";
    if (this.status === 429) return "Too many requests. Please try again later.";
    if (this.isServerError) return "Server error. Please try again later.";
    return this.message;
  }

  toJSON() {
    return {
      name: this.name,
      message: this.message,
      status: this.status,
      code: this.code,
      details: this.details,
      timestamp: this.timestamp,
      path: this.path,
      stack: this.stack,
    };
  }
}

// Export actual ApiError for compatibility
export const ApiError = MockApiError;

// Complete auth state change mock
export const createMockAuthStateChange = () =>
  vi
    .fn()
    .mockImplementation((_callback: (event: string, session: unknown) => void) => ({
      data: { subscription: { unsubscribe: vi.fn() } },
    }));

// Complete table builder mock that returns complete query builder
export const createMockTableBuilder = (
  mockResponse: { data: unknown; error: unknown } = { data: null, error: null }
) =>
  vi
    .fn()
    .mockImplementation(() =>
      createCompleteQueryBuilder(mockResponse.data, mockResponse.error)
    );

// For functions that need table-specific logic
export const createMockTableBuilderWithTable = (
  mockResponse: { data: unknown; error: unknown } = { data: null, error: null }
) =>
  vi
    .fn()
    .mockImplementation((_table: string) =>
      createCompleteQueryBuilder(mockResponse.data, mockResponse.error)
    );

// Create a test wrapper with QueryClient
import { QueryClient } from "@tanstack/react-query";

export const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });

// Enhanced toast mock factory
export const createMockToast = () => {
  const mockToast = vi.fn((_props: any) => ({
    id: `toast-${Date.now()}`,
    dismiss: vi.fn(),
    update: vi.fn(),
  }));

  return {
    toast: mockToast,
    useToast: vi.fn(() => ({
      toast: mockToast,
      dismiss: vi.fn(),
      toasts: [],
    })),
  };
};

// Enhanced search store mock factory
export const createMockSearchStore = () => ({
  currentSearchType: null,
  currentParams: null,
  hasActiveFilters: false,
  hasResults: false,
  isSearching: false,
  initializeSearch: vi.fn(),
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
});

// Enhanced user store mock factory
export const createMockUserStore = (overrides = {}) => ({
  profile: {
    id: "test-user-id",
    email: "test@example.com",
    name: "Test User",
    twoFactorEnabled: false,
    settings: {
      notifications: true,
      privacy: "public",
    },
    ...overrides,
  },
  preferences: {
    theme: "light",
    language: "en",
  },
  insights: null,
  isLoading: false,
  error: null,
  updateProfile: vi.fn().mockResolvedValue({}),
  updatePreferences: vi.fn().mockResolvedValue({}),
  refreshInsights: vi.fn().mockResolvedValue({}),
  clearError: vi.fn(),
});

// Environment variable mock helper
export const mockProcessEnv = (env: Record<string, string>) => {
  const originalEnv = process.env;
  Object.entries(env).forEach(([key, value]) => {
    Object.defineProperty(process.env, key, {
      value,
      writable: true,
      configurable: true,
    });
  });

  return () => {
    process.env = originalEnv;
  };
};
