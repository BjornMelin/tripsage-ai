/**
 * @fileoverview Typed factory helpers for mocking Supabase and TanStack Query.
 */

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

interface QueryResponse<TData> {
  data: TData;
  error: unknown;
}

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

type AuthMethodMock<T extends (...args: any[]) => unknown> = MockInstance<T> & T;

export type SupabaseAuthMock = {
  [K in SupportedAuthMethod]: AuthClient[K] extends (...args: any[]) => any
    ? AuthMethodMock<AuthClient[K]>
    : never;
};

const createMockFn = <T extends (...args: any[]) => unknown>(
  implementation: T
): AuthMethodMock<T> => vi.fn(implementation) as unknown as AuthMethodMock<T>;

const createMockUser = (): User => ({
  id: "mock-user-id",
  app_metadata: {},
  user_metadata: {},
  aud: "authenticated",
  email: "mock-user@example.com",
  created_at: new Date(0).toISOString(),
});

const createMockSession = (user: User): Session => ({
  access_token: "mock-access-token",
  refresh_token: "mock-refresh-token",
  expires_in: 3_600,
  token_type: "bearer",
  user,
});

const createMockSubscription = (callback: Subscription["callback"]): Subscription => ({
  id: "mock-subscription-id",
  callback,
  unsubscribe: vi.fn(),
});

/**
 * Build a Supabase auth client mock that mirrors common behaviours used in tests.
 */
export const createMockSupabaseAuthClient = (): SupabaseAuthMock => {
  const user = createMockUser();
  const session = createMockSession(user);

  const getSession = createMockFn<AuthClient["getSession"]>(async () => ({
    data: { session: null },
    error: null,
  }));

  const onAuthStateChange = createMockFn<AuthClient["onAuthStateChange"]>(
    (callback) => ({
      data: { subscription: createMockSubscription(callback) },
    })
  );

  const signUp = createMockFn<AuthClient["signUp"]>(async () => ({
    data: { user, session },
    error: null,
  }));

  const signInWithPassword = createMockFn<AuthClient["signInWithPassword"]>(
    async () => ({
      data: { user, session, weakPassword: undefined },
      error: null,
    })
  );

  const signOut = createMockFn<AuthClient["signOut"]>(async () => ({
    error: null,
  }));

  const resetPasswordForEmail = createMockFn<AuthClient["resetPasswordForEmail"]>(
    async () => ({
      data: {},
      error: null,
    })
  );

  const updateUser = createMockFn<AuthClient["updateUser"]>(async () => ({
    data: { user },
    error: null,
  }));

  const getUser = createMockFn<AuthClient["getUser"]>(async () => ({
    data: { user },
    error: null,
  }));

  const signInWithOAuth = createMockFn<AuthClient["signInWithOAuth"]>(async () => ({
    data: { provider: "github", url: "" },
    error: null,
  }));

  const refreshSession = createMockFn<AuthClient["refreshSession"]>(async () => ({
    data: { session, user },
    error: null,
  }));

  return {
    getSession,
    onAuthStateChange,
    signUp,
    signInWithPassword,
    signOut,
    resetPasswordForEmail,
    updateUser,
    getUser,
    signInWithOAuth,
    refreshSession,
  };
};

class MockQueryBuilder<TAll, TSingle = TAll>
  implements PromiseLike<QueryResponse<TAll>>
{
  private data: TAll;
  private singleData: TSingle;
  private error: unknown;

  readonly select = vi.fn(() => this);
  readonly insert = vi.fn((rows: TAll) => {
    this.data = rows;
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
    initialData: TAll,
    private readonly toSingle: (data: TAll) => TSingle,
    error: unknown = null
  ) {
    this.data = initialData;
    this.singleData = toSingle(initialData);
    this.error = error;
  }

  then<TResult1 = QueryResponse<TAll>, TResult2 = never>(
    onFulfilled?:
      | ((value: QueryResponse<TAll>) => TResult1 | PromiseLike<TResult1>)
      | null
      | undefined,
    onRejected?:
      | ((reason: unknown) => TResult2 | PromiseLike<TResult2>)
      | null
      | undefined
  ): Promise<TResult1 | TResult2> {
    return Promise.resolve({ data: this.data, error: this.error }).then(
      onFulfilled,
      onRejected
    );
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
      (rows) => rows[0] ?? null
    );
  });

  const channel = vi.fn(() => ({
    on: vi.fn().mockReturnThis(),
    subscribe: vi.fn(() => ({ unsubscribe: vi.fn() })),
  }));

  const storageFrom = vi.fn(() => ({
    upload: vi.fn(async () => ({ data: null, error: null })),
    remove: vi.fn(async () => ({ data: null, error: null })),
    download: vi.fn(async () => ({ data: null, error: null })),
    list: vi.fn(async () => ({ data: [], error: null })),
  }));

  const storage = {
    from: storageFrom,
    getBucket: vi.fn(async () => ({ data: null, error: null })),
    getBucketId: vi.fn(() => "attachments"),
  } as unknown as SupabaseClient<UnknownRecord>["storage"];

  return {
    auth,
    from,
    channel,
    storage,
    removeChannel: vi.fn(),
  } as unknown as SupabaseClient<UnknownRecord>;
};

/**
 * Build a TanStack Query result mock for unit tests.
 */
export const createMockUseQueryResult = <TData, TError = Error>(
  data: TData | null = null,
  error: TError | null = null,
  isLoading = false,
  isError = false
): UseQueryResult<TData, TError> => {
  const result: any = {
    data: (data ?? undefined) as TData | undefined,
    error: (error ?? null) as TError | null,
    isLoading,
    isError,
    isSuccess: !isLoading && !isError && data !== null,
    isPending: isLoading,
    isFetching: false,
    isFetched: !isLoading,
    isFetchedAfterMount: !isLoading,
    isRefetching: false,
    isLoadingError: isError && isLoading,
    isRefetchError: false,
    isPlaceholderData: false,
    isPaused: false,
    isStale: false,
    dataUpdatedAt: Date.now(),
    errorUpdatedAt: error ? Date.now() : 0,
    failureCount: error ? 1 : 0,
    failureReason: error ?? null,
    errorUpdateCount: error ? 1 : 0,
    status: isLoading ? "pending" : isError ? "error" : "success",
    fetchStatus: "idle",
    isInitialLoading: isLoading,
    promise: Promise.resolve(data as TData),
    isEnabled: !isLoading,
  };

  result.refetch = vi.fn(async () => result);

  return result as UseQueryResult<TData, TError>;
};

/**
 * Build a placeholder UseInfiniteQueryResult mock.
 */
export const createMockInfiniteQueryResult = <TData, TError = Error>(
  overrides: Partial<UseInfiniteQueryResult<TData, TError>> = {}
): UseInfiniteQueryResult<TData, TError> => {
  const result: any = {
    data: undefined,
    error: null,
    status: "success",
    fetchStatus: "idle",
    isLoading: false,
    isError: false,
    isSuccess: true,
    isFetching: false,
    isFetchingNextPage: false,
    isFetchingPreviousPage: false,
    hasNextPage: false,
    hasPreviousPage: false,
    fetchNextPage: vi.fn(),
    fetchPreviousPage: vi.fn(),
    refetch: vi.fn(),
    ...overrides,
  };

  return result as UseInfiniteQueryResult<TData, TError>;
};
