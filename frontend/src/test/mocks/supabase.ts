/**
 * @fileoverview Canonical Supabase mock factory for tests.
 *
 * Consolidates all Supabase mock implementations into a single source of truth.
 * Supports both client-side and server-side Supabase mocks with rich auth capabilities
 * and optional insert capture for testing.
 */

import type {
  Session,
  Subscription,
  SupabaseClient,
  User,
} from "@supabase/supabase-js";
import type { MockInstance } from "vitest";
import { vi } from "vitest";
import type { TypedServerSupabase } from "@/lib/supabase/server";

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
 * Configuration for Supabase mock factory with insert capture support.
 */
export interface SupabaseMockConfig {
  /**
   * Array to capture insert payloads.
   * All insert operations will push their payloads to this array.
   */
  insertCapture?: unknown[];

  /**
   * Result to return from select queries.
   * Supports async single() queries that return { data, error }.
   */
  selectResult?: {
    data: unknown;
    error: unknown;
  };

  /**
   * Optional user to return from auth.getUser().
   */
  user?: User | null;
}

/**
 * Creates a mocked function that combines Vitest MockInstance with the original type.
 */
const CREATE_MOCK_FN = <T extends (...args: never[]) => unknown>(
  implementation: T
): AuthMethodMock<T> => vi.fn(implementation) as unknown as AuthMethodMock<T>;

/**
 * Creates a mock User object with default test values.
 */
const CREATE_MOCK_USER = (): User =>
  ({
    app_metadata: {},
    aud: "authenticated",
    created_at: new Date(0).toISOString(),
    email: "mock-user@example.com",
    id: "mock-user-id",
    user_metadata: {},
  }) as User;

/**
 * Creates a mock Session object for a given user.
 */
const CREATE_MOCK_SESSION = (user: User): Session =>
  ({
    access_token: "mock-access-token",
    expires_in: 3_600,
    refresh_token: "mock-refresh-token",
    token_type: "bearer",
    user,
  }) as Session;

/**
 * Creates a mock Subscription object with a callback function.
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
 * @param user Optional user to return from getUser().
 * @returns A fully mocked Supabase auth client with type-safe method signatures
 */
export const createMockSupabaseAuthClient = (user?: User | null): SupabaseAuthMock => {
  const mockUser = user ?? CREATE_MOCK_USER();
  const session = CREATE_MOCK_SESSION(mockUser);

  const getSession = CREATE_MOCK_FN<AuthClient["getSession"]>(() => {
    if (mockUser) {
      return Promise.resolve({ data: { session }, error: null });
    }
    return Promise.resolve({ data: { session: null }, error: null });
  });

  const onAuthStateChange = CREATE_MOCK_FN<AuthClient["onAuthStateChange"]>(
    (callback) => ({
      data: { subscription: CREATE_MOCK_SUBSCRIPTION(callback) },
    })
  );

  const signUp = CREATE_MOCK_FN<AuthClient["signUp"]>(async () => ({
    data: { session, user: mockUser },
    error: null,
  }));

  const signInWithPassword = CREATE_MOCK_FN<AuthClient["signInWithPassword"]>(
    async () => ({
      data: { session, user: mockUser, weakPassword: undefined },
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
    data: { user: mockUser },
    error: null,
  }));

  const getUser = CREATE_MOCK_FN<AuthClient["getUser"]>(async () => ({
    data: { user: mockUser },
    error: null,
  }));

  const signInWithOauth = CREATE_MOCK_FN<AuthClient["signInWithOAuth"]>(async () => ({
    data: { provider: "github", url: "" },
    error: null,
  }));

  const refreshSession = CREATE_MOCK_FN<AuthClient["refreshSession"]>(async () => ({
    data: { session, user: mockUser },
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
  singleData: S;
  /** Mock error returned by query methods. */
  error: unknown;
  /** Optional insert capture array. */
  insertCapture?: unknown[];

  /** Mock select method - chains to allow further filtering. */
  readonly select = vi.fn(() => this);
  /** Mock insert method - updates singleData with transformed input and captures payloads. */
  readonly insert = vi.fn((rows: T) => {
    this.singleData = this.toSingle(rows);
    if (this.insertCapture) {
      this.insertCapture.push(rows);
    }
    return this;
  });
  /** Mock update method - chains to allow further filtering. */
  readonly update = vi.fn(() => this);
  /** Mock delete method - chains to allow further filtering. */
  readonly delete = vi.fn(() => this);
  /** Mock eq method - chains to allow further filtering. */
  readonly eq = vi.fn(() => this);
  /** Mock gte method - chains to allow further filtering. */
  readonly gte = vi.fn(() => this);
  /** Mock lte method - chains to allow further filtering. */
  readonly lte = vi.fn(() => this);
  /** Mock order method - chains to allow further filtering. */
  readonly order = vi.fn(() => this);
  /** Mock limit method - chains to allow further filtering. */
  readonly limit = vi.fn(() => this);
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
   * @param insertCapture Optional array to capture insert payloads
   */
  constructor(
    initialData: T,
    readonly toSingle: (data: T) => S,
    error: unknown = null,
    insertCapture?: unknown[]
  ) {
    this.singleData = toSingle(initialData);
    this.error = error;
    this.insertCapture = insertCapture;
  }
}

/**
 * Creates a complete Supabase client mock with auth, database, and storage methods.
 * Useful for testing components that interact with the full Supabase API.
 *
 * @param config Optional configuration for insert capture and select results
 * @returns A fully mocked Supabase client with auth, database, and storage methods
 */
export const createMockSupabaseClient = (
  config?: SupabaseMockConfig
): SupabaseClient<UnknownRecord> => {
  const { insertCapture, selectResult, user } = config ?? {};
  const auth = createMockSupabaseAuthClient(user);

  const from = vi.fn((_table: string) => {
    return new MockQueryBuilder<UnknownRecord[], UnknownRecord | null>(
      [],
      (rows: UnknownRecord[]) => rows[0] ?? null,
      selectResult?.error ?? null,
      insertCapture
    );
  });

  // Override single() if selectResult is provided
  if (selectResult) {
    from.mockImplementation((_table: string) => {
      const builder = new MockQueryBuilder<UnknownRecord[], UnknownRecord | null>(
        [],
        () => selectResult.data as UnknownRecord | null,
        selectResult.error ?? null,
        insertCapture
      );
      // Override single method using Object.defineProperty to bypass readonly
      Object.defineProperty(builder, "single", {
        configurable: true,
        value: vi.fn(async () => ({
          data: selectResult.data,
          error: selectResult.error,
        })),
        writable: true,
      });
      return builder;
    });
  }

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
 * Creates a mock Supabase client factory for server-side testing.
 *
 * Returns a function that creates a mock TypedServerSupabase client with:
 * - `from(table)` method that returns insert/select builders
 * - `insert()` that captures payloads to insertCapture array (if provided)
 * - `select()` that returns a chainable query builder ending in single()
 *
 * @param config Configuration for insert capture and select results
 * @returns Async function that returns a mock TypedServerSupabase client
 *
 * @example
 * ```typescript
 * const insertCapture: unknown[] = [];
 * const supabase = createMockSupabaseFactory({
 *   insertCapture,
 *   selectResult: { data: { id: 1, user_id: "user-1" }, error: null }
 * });
 *
 * const client = await supabase();
 * const result = await client.from("trips").select().eq("id", 1).eq("user_id", "user-1").single();
 * // result.data === { id: 1, user_id: "user-1" }
 * // insertCapture contains all insert payloads
 * ```
 */
export function createMockSupabaseFactory(
  config: SupabaseMockConfig
): () => Promise<TypedServerSupabase> {
  const { insertCapture, selectResult = { data: null, error: null }, user } = config;

  return () => {
    const client = createMockSupabaseClient({ insertCapture, selectResult, user });
    return Promise.resolve(client as unknown as TypedServerSupabase);
  };
}

/**
 * Sets up Supabase client mocks for a test file using vi.mock().
 * Call this at the top level of test files that use Supabase.
 *
 * @example
 * ```ts
 * import { setupSupabaseMocks } from "@/test/mocks/supabase";
 * setupSupabaseMocks();
 * ```
 */
export function setupSupabaseMocks(): void {
  const MOCK_SUPABASE = createMockSupabaseClient();

  vi.mock("@/lib/supabase", () => ({
    createClient: () => MOCK_SUPABASE,
    getBrowserClient: () => MOCK_SUPABASE,
    useSupabase: () => MOCK_SUPABASE,
  }));
}
