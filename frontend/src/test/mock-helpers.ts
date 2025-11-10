import type {
  Session,
  Subscription,
  SupabaseClient,
  User,
} from "@supabase/supabase-js";
import type { UseInfiniteQueryResult, UseQueryResult } from "@tanstack/react-query";
import type { MockInstance } from "vitest";
import { vi } from "vitest";

/** Generic record type for unknown database row structures. */
type UnknownRecord = Record<string, unknown>;

/** Type alias for Supabase auth client methods. */
type AuthClient = SupabaseClient<UnknownRecord>["auth"];

/** Supported authentication methods that can be mocked. */
type SupportedAuthMethod =
  | "getSession"
  | "onAuthStateChange"
  | "signUp"
  | "signInWithPassword"
  | "signOut"
  | "resetPasswordForEmail"
  | "updateUser"
  | "getUser"
  | "signInWithOAuth"
  | "refreshSession";

/**
 * Mock type that combines Vitest MockInstance with the original function type.
 * This allows mocks to be used as both spies and the original function signature.
 */
type AuthMethodMock<T extends (...args: never[]) => unknown> = MockInstance<T> & T;

/**
 * Type definition for a complete Supabase auth client mock.
 * All supported auth methods are mocked with their original signatures.
 */
export type SupabaseAuthMock = {
  [K in SupportedAuthMethod]: AuthMethodMock<AuthClient[K]>;
};

/**
 * Creates a mocked function that combines Vitest MockInstance with the original type.
 * This allows the mock to be used both as a spy and with the original function signature.
 *
 * @param implementation The function implementation to mock
 * @returns A mocked function that can be used as both MockInstance and the original type
 */
const CREATE_MOCK_FN = <T extends (...args: never[]) => unknown>(
  implementation: T
): AuthMethodMock<T> => vi.fn(implementation) as unknown as AuthMethodMock<T>;

/**
 * Creates a mock User object with default test values.
 *
 * @returns A mock User object for testing
 */
const CREATE_MOCK_USER = (): User =>
  ({
    // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case
    app_metadata: {},
    aud: "authenticated",
    // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case
    created_at: new Date(0).toISOString(),
    email: "mock-user@example.com",
    id: "mock-user-id",
    // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case
    user_metadata: {},
  }) as User;

/**
 * Creates a mock Session object for a given user.
 *
 * @param user The user associated with the session
 * @returns A mock Session object for testing
 */
const CREATE_MOCK_SESSION = (user: User): Session =>
  ({
    // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case
    access_token: "mock-access-token",
    // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case
    expires_in: 3_600,
    // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case
    refresh_token: "mock-refresh-token",
    // biome-ignore lint/style/useNamingConvention: Supabase API uses snake_case
    token_type: "bearer",
    user,
  }) as Session;

/**
 * Creates a mock Subscription object with a callback function.
 *
 * @param callback The callback function for auth state changes
 * @returns A mock Subscription object for testing
 */
const CREATE_MOCK_SUBSCRIPTION = (
  callback: Subscription["callback"]
): Subscription => ({
  callback,
  id: "mock-subscription-id",
  unsubscribe: vi.fn(),
});

/**
 * Creates a complete Supabase auth client mock with all supported methods.
 * Each auth method returns sensible default values for testing purposes.
 *
 * @returns A fully mocked Supabase auth client with type-safe method signatures
 */
export const createMockSupabaseAuthClient = (): SupabaseAuthMock => {
  const user = CREATE_MOCK_USER();
  const session = CREATE_MOCK_SESSION(user);

  const getSession = CREATE_MOCK_FN<AuthClient["getSession"]>(async () => ({
    data: { session: null },
    error: null,
  }));

  const onAuthStateChange = CREATE_MOCK_FN<AuthClient["onAuthStateChange"]>(
    (callback) => ({
      data: { subscription: CREATE_MOCK_SUBSCRIPTION(callback) },
    })
  );

  const signUp = CREATE_MOCK_FN<AuthClient["signUp"]>(async () => ({
    data: { session, user },
    error: null,
  }));

  const signInWithPassword = CREATE_MOCK_FN<AuthClient["signInWithPassword"]>(
    async () => ({
      data: { session, user, weakPassword: undefined },
      error: null,
    })
  );

  const signOut = CREATE_MOCK_FN<AuthClient["signOut"]>(async () => ({
    error: null,
  }));

  const resetPasswordForEmail = CREATE_MOCK_FN<AuthClient["resetPasswordForEmail"]>(
    async () => ({
      data: {},
      error: null,
    })
  );

  const updateUser = CREATE_MOCK_FN<AuthClient["updateUser"]>(async () => ({
    data: { user },
    error: null,
  }));

  const getUser = CREATE_MOCK_FN<AuthClient["getUser"]>(async () => ({
    data: { user },
    error: null,
  }));

  const signInWithOauth = CREATE_MOCK_FN<AuthClient["signInWithOAuth"]>(async () => ({
    data: { provider: "github", url: "" },
    error: null,
  }));

  const refreshSession = CREATE_MOCK_FN<AuthClient["refreshSession"]>(async () => ({
    data: { session, user },
    error: null,
  }));

  const result = {
    getSession,
    getUser,
    onAuthStateChange,
    refreshSession,
    resetPasswordForEmail,
    signInWithPassword,
    signOut,
    signUp,
    updateUser,
  };
  (result as Record<string, unknown>).signInWithOAuth = signInWithOauth;
  return result as SupabaseAuthMock;
};

/**
 * Mock implementation of Supabase's PostgrestFilterBuilder for testing.
 * Provides chainable query methods that return mock data.
 */
class MockQueryBuilder<T, S = T> {
  /** Mock data returned by single() and maybeSingle() methods. */
  private singleData: S;
  /** Mock error returned by query methods. */
  private error: unknown;

  /** Mock select method - chains to allow further filtering. */
  readonly select = vi.fn(() => this);
  /** Mock insert method - updates singleData with transformed input. */
  readonly insert = vi.fn((rows: T) => {
    this.singleData = this.toSingle(rows);
    return this;
  });
  /** Mock update method - chains to allow further filtering. */
  readonly update = vi.fn(() => this);
  /** Mock delete method - chains to allow further filtering. */
  readonly delete = vi.fn(() => this);
  /** Mock eq method - chains to allow further filtering. */
  readonly eq = vi.fn(() => this);
  /** Mock order method - chains to allow further filtering. */
  readonly order = vi.fn(() => this);
  /** Mock range method - chains to allow further filtering. */
  readonly range = vi.fn(() => this);
  /** Mock single method - returns single data result. */
  readonly single = vi.fn(async () => ({
    data: this.singleData,
    error: this.error,
  }));
  /** Mock maybeSingle method - returns single data result (nullable). */
  readonly maybeSingle = vi.fn(async () => ({
    data: this.singleData,
    error: this.error,
  }));

  /**
   * Creates a new MockQueryBuilder instance.
   *
   * @param initialData Initial data for the mock
   * @param toSingle Function to transform array data to single result
   * @param error Optional error to return from queries
   */
  constructor(
    initialData: T,
    private readonly toSingle: (data: T) => S,
    error: unknown = null
  ) {
    this.singleData = toSingle(initialData);
    this.error = error;
  }
}

/**
 * Creates a complete Supabase client mock with auth, database, and storage methods.
 * Useful for testing components that interact with the full Supabase API.
 *
 * @returns A fully mocked Supabase client with auth, database, and storage methods
 */
export const createMockSupabaseClient = (): SupabaseClient<UnknownRecord> => {
  const auth = createMockSupabaseAuthClient();

  const from = vi.fn((_table: string) => {
    return new MockQueryBuilder<UnknownRecord[], UnknownRecord | null>(
      [],
      (rows: UnknownRecord[]) => rows[0] ?? null
    );
  });

  const channel = vi.fn(() => ({
    on: vi.fn().mockReturnThis(),
    subscribe: vi.fn(() => ({ unsubscribe: vi.fn() })),
  }));

  const storageFrom = vi.fn(() => ({
    download: vi.fn(async () => ({ data: null, error: null })),
    list: vi.fn(async () => ({ data: [], error: null })),
    remove: vi.fn(async () => ({ data: null, error: null })),
    upload: vi.fn(async () => ({ data: null, error: null })),
  }));

  const storage = {
    from: storageFrom,
    getBucket: vi.fn(async () => ({ data: null, error: null })),
    getBucketId: vi.fn(() => "attachments"),
  } as unknown as SupabaseClient<UnknownRecord>["storage"];

  return {
    auth,
    channel,
    from,
    removeChannel: vi.fn(),
    storage,
  } as unknown as SupabaseClient<UnknownRecord>;
};

/**
 * Creates a mock TanStack Query result for testing React Query hooks.
 * Provides realistic query state with customizable data, error, and loading states.
 *
 * @param data Optional data to return from the query
 * @param error Optional error to return from the query
 * @param isLoading Whether the query is in loading state
 * @param isError Whether the query is in error state
 * @returns A complete UseQueryResult mock with all required properties
 */
export const createMockUseQueryResult = <T, E = Error>(
  data: T | null = null,
  error: E | null = null,
  isLoading = false,
  isError = false
): UseQueryResult<T, E> => {
  const refetch = vi.fn();
  const result = {
    data: (data ?? undefined) as T | undefined,
    dataUpdatedAt: Date.now(),
    error: (error ?? null) as E | null,
    errorUpdateCount: error ? 1 : 0,
    errorUpdatedAt: error ? Date.now() : 0,
    failureCount: error ? 1 : 0,
    failureReason: error ?? null,
    fetchStatus: "idle",
    isEnabled: !isLoading,
    isError,
    isFetched: !isLoading,
    isFetchedAfterMount: !isLoading,
    isFetching: false,
    isInitialLoading: isLoading,
    isLoading,
    isLoadingError: isError && isLoading,
    isPaused: false,
    isPending: isLoading,
    isPlaceholderData: false,
    isRefetchError: false,
    isRefetching: false,
    isStale: false,
    isSuccess: !isLoading && !isError && data !== null,
    promise: Promise.resolve(data as T),
    refetch,
    status: isLoading ? "pending" : isError ? "error" : "success",
  } as UseQueryResult<T, E>;

  refetch.mockImplementation(async () => result);

  return result;
};

/**
 * Creates a mock TanStack Query infinite query result for testing infinite scroll hooks.
 * Provides default values for all infinite query properties with optional overrides.
 *
 * @param overrides Optional properties to override in the mock result
 * @returns A complete UseInfiniteQueryResult mock with realistic default values
 */
export const createMockInfiniteQueryResult = <T, E = Error>(
  overrides: Partial<UseInfiniteQueryResult<T, E>> = {}
): UseInfiniteQueryResult<T, E> => {
  const result = {
    data: undefined,
    error: null,
    fetchNextPage: vi.fn(),
    fetchPreviousPage: vi.fn(),
    fetchStatus: "idle",
    hasNextPage: false,
    hasPreviousPage: false,
    isError: false,
    isFetching: false,
    isFetchingNextPage: false,
    isFetchingPreviousPage: false,
    isLoading: false,
    isPending: false,
    isSuccess: true,
    refetch: vi.fn(),
    status: "success",
    ...overrides,
  } as UseInfiniteQueryResult<T, E>;

  return result;
};
