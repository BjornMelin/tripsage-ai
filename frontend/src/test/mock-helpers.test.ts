import type {
  Session,
  Subscription,
  SupabaseClient,
  User,
} from "@supabase/supabase-js";
import type { UseInfiniteQueryResult, UseQueryResult } from "@tanstack/react-query";
import type { MockInstance } from "vitest";
import { vi } from "vitest";

type UnknownRecord = Record<string, unknown>;

type AuthClient = SupabaseClient<UnknownRecord>["auth"];

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

type AuthMethodMock<T extends (...args: any[]) => any> = MockInstance<T> & T;

export type SupabaseAuthMock = {
  [K in SupportedAuthMethod]: AuthClient[K] extends (...args: any[]) => any
    ? AuthMethodMock<AuthClient[K]>
    : never;
};

const CREATE_MOCK_FN = <T extends (...args: any[]) => any>(
  implementation: T
): AuthMethodMock<T> => vi.fn(implementation) as unknown as AuthMethodMock<T>;

const CREATE_MOCK_USER = (): User =>
  ({
    app_metadata: {},
    aud: "authenticated",
    created_at: new Date(0).toISOString(),
    email: "mock-user@example.com",
    id: "mock-user-id",
    user_metadata: {},
  }) as User;

const CREATE_MOCK_SESSION = (user: User): Session =>
  ({
    access_token: "mock-access-token",
    expires_in: 3_600,
    refresh_token: "mock-refresh-token",
    token_type: "bearer",
    user,
  }) as Session;

const CREATE_MOCK_SUBSCRIPTION = (
  callback: Subscription["callback"]
): Subscription => ({
  callback,
  id: "mock-subscription-id",
  unsubscribe: vi.fn(),
});

/**
 * Build a Supabase auth client mock that mirrors common behaviours used in tests.
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
  (result as any).signInWithOAuth = signInWithOauth;
  return result as SupabaseAuthMock;
};

/**
 * Mock query builder class
 */
class MockQueryBuilder<T, S = T> {
  private singleData: S;
  private error: unknown;

  readonly select = vi.fn(() => this);
  readonly insert = vi.fn((rows: T) => {
    this.singleData = this.toSingle(rows);
    return this;
  });
  readonly update = vi.fn(() => this);
  readonly delete = vi.fn(() => this);
  readonly eq = vi.fn(() => this);
  readonly order = vi.fn(() => this);
  readonly range = vi.fn(() => this);
  readonly single = vi.fn(async () => ({
    data: this.singleData,
    error: this.error,
  }));
  readonly maybeSingle = vi.fn(async () => ({
    data: this.singleData,
    error: this.error,
  }));

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
 * Create a typed Supabase client mock with chainable query builders.
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
 * Build a TanStack Query result mock for unit tests.
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
 * Build a placeholder UseInfiniteQueryResult mock.
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
