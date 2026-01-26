/**
 * @fileoverview Canonical Supabase mock factory for tests.
 *
 * Consolidates all Supabase mock implementations into a single source of truth.
 * Supports both client-side and server-side Supabase mocks with rich auth capabilities
 * and optional insert capture for testing.
 */

import type { Session, SupabaseClient, User } from "@supabase/supabase-js";
import { AuthError, createClient } from "@supabase/supabase-js";
import { vi } from "vitest";
import type { Database } from "@/lib/supabase/database.types";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { TEST_USER_ID } from "@/test/helpers/ids";

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
   * Array to capture update (PATCH) payloads.
   * All update operations will push their payloads to this array.
   */
  updateCapture?: unknown[];

  /**
   * Result to return from select queries.
   * Supports async single() queries that return { data, error }.
   *
   * Note: when `selectResult.data` is an empty array and the test has previously
   * inserted rows into the same table via this mock, the mock will return those
   * inserted rows on subsequent GETs. This supports common "insert then select"
   * test patterns, but can mask mismatches when a test expects an empty result.
   *
   * To opt out for a specific table, provide an explicit `selectResults[table]`
   * entry (even with `data: []`) so the mock does not fall back to inserted rows.
   */
  selectResult?: {
    count?: number | null;
    data: unknown;
    error: unknown;
  };

  /**
   * Table-specific select responses keyed by table/view name.
   *
   * When set, these take precedence over `selectResult`.
   */
  selectResults?: Record<
    string,
    { count?: number | null; data: unknown; error: unknown }
  >;

  /**
   * RPC results keyed by function name.
   *
   * If a function is not present, calls return `{ data: null, error: null }`.
   */
  rpcResults?: Record<string, { data: unknown; error: unknown; count?: number | null }>;

  /**
   * Force insert errors for specific tables (keyed by table name).
   */
  insertErrors?: Record<string, unknown>;

  /**
   * Optional fixed token used for storage signed URL generation.
   */
  storageToken?: string;

  /**
   * Optional user to return from auth.getUser().
   */
  user?: User | null | Partial<User>;
}

/**
 * Creates a mock User object with default test values.
 */
const createMockUser = (overrides?: Partial<User>): User => ({
  app_metadata: {},
  aud: "authenticated",
  created_at: new Date(0).toISOString(),
  email: "mock-user@example.com",
  id: TEST_USER_ID,
  user_metadata: {},
  ...overrides,
});

/**
 * Creates a mock Session object for a given user.
 */
const createMockSession = (user: User): Session => ({
  access_token: "mock-access-token",
  expires_in: 3_600,
  refresh_token: "mock-refresh-token",
  token_type: "bearer",
  user,
});

/**
 * Mutable state backing a mock Supabase client.
 */
export type SupabaseMockState = {
  autoIncrement: Map<string, number>;
  insertCapture: unknown[];
  insertByTable: Map<string, unknown[]>;
  insertErrorsByTable: Map<string, unknown>;
  updateCapture: unknown[];
  updateByTable: Map<string, unknown[]>;
  requests: Array<{ body?: unknown | null; method: string; url: string }>;
  rpcResults: Map<string, { count?: number | null; data: unknown; error: unknown }>;
  selectByTable: Map<string, { count?: number | null; data: unknown; error: unknown }>;
  selectResult: { count?: number | null; data: unknown; error: unknown };
  storageToken: string;
  user: User | null;
};

const STATE = new WeakMap<SupabaseClient<Database>, SupabaseMockState>();

function jsonResponse(
  body: unknown,
  init?: { headers?: HeadersInit; status?: number }
): Response {
  return new Response(JSON.stringify(body), {
    headers: {
      "content-type": "application/json",
      ...(init?.headers ?? {}),
    },
    status: init?.status ?? 200,
  });
}

function makeContentRange(
  count: number | null | undefined,
  rows: unknown
): string | null {
  if (typeof count !== "number") return null;
  const len = Array.isArray(rows) ? rows.length : rows ? 1 : 0;
  if (len === 0) {
    // PostgREST convention for empty result sets.
    return `*/${count}`;
  }
  return `0-${len - 1}/${count}`;
}

function makePostgrestErrorPayload(error: unknown) {
  if (error instanceof Error) {
    return { code: "MOCK", details: null, hint: null, message: error.message };
  }
  if (typeof error === "string") {
    return { code: "MOCK", details: null, hint: null, message: error };
  }
  return { code: "MOCK", details: error ?? null, hint: null, message: "Mock error" };
}

function parseJsonBody(body: BodyInit | null | undefined): unknown | null {
  if (body == null) return null;

  if (typeof body === "string") {
    try {
      return JSON.parse(body) as unknown;
    } catch {
      return null;
    }
  }

  if (body instanceof ArrayBuffer || ArrayBuffer.isView(body)) {
    try {
      const view = body instanceof ArrayBuffer ? new Uint8Array(body) : body;
      const bytes = ArrayBuffer.isView(view)
        ? new Uint8Array(view.buffer, view.byteOffset, view.byteLength)
        : null;
      if (!bytes) return null;
      const text = new TextDecoder().decode(bytes);
      return JSON.parse(text) as unknown;
    } catch {
      return null;
    }
  }

  if (body instanceof URLSearchParams) {
    const text = body.toString();
    try {
      return JSON.parse(text) as unknown;
    } catch {
      return text;
    }
  }

  return null;
}

function flattenInsertedRows(value: unknown): unknown[] {
  if (!value) return [];
  if (Array.isArray(value)) return value;
  if (typeof value === "object") return [value];
  return [];
}

function getNextAutoIncrement(state: SupabaseMockState, table: string): number {
  const current = state.autoIncrement.get(table) ?? 0;
  const next = current + 1;
  state.autoIncrement.set(table, next);
  return next;
}

function applyRowDefaults(
  state: SupabaseMockState,
  table: string,
  row: unknown
): unknown {
  if (!row || typeof row !== "object") return row;
  const record = row as Record<string, unknown>;

  if (table === "chat_sessions") {
    if (record.created_at === undefined) record.created_at = null;
    if (record.updated_at === undefined) record.updated_at = record.created_at ?? null;
    if (record.metadata === undefined) record.metadata = null;
    if (record.trip_id === undefined) record.trip_id = null;
    return record;
  }

  if (table === "chat_messages") {
    if (typeof record.id !== "number") {
      record.id = getNextAutoIncrement(state, table);
    }
    if (record.created_at === undefined) record.created_at = null;
    if (record.metadata === undefined) record.metadata = null;
    return record;
  }

  if (table === "file_attachments") {
    if (record.created_at === undefined) record.created_at = null;
    if (record.updated_at === undefined) record.updated_at = null;
    if (record.metadata === undefined) record.metadata = null;
    if (record.virus_scan_result === undefined) record.virus_scan_result = null;
    if (record.virus_scan_status === undefined) record.virus_scan_status = "pending";
    return record;
  }

  if (table === "chat_tool_calls") {
    if (typeof record.id !== "number") {
      record.id = getNextAutoIncrement(state, table);
    }
    if (record.created_at === undefined) record.created_at = null;
    if (record.updated_at === undefined) record.updated_at = null;
    if (record.error_message === undefined) record.error_message = null;
    return record;
  }

  return record;
}

function hydrateInsertedRows(
  state: SupabaseMockState,
  table: string,
  payload: unknown
): unknown[] {
  const rows = flattenInsertedRows(payload);
  if (rows.length === 0) return [];
  return rows.map((row) => applyRowDefaults(state, table, row));
}

function applyEqFilters(rows: unknown, searchParams: URLSearchParams): unknown {
  if (!Array.isArray(rows)) return rows;

  const filterEntries = Array.from(searchParams.entries()).filter(([key, value]) => {
    if (key === "select" || key === "limit" || key === "offset" || key === "order") {
      return false;
    }
    return value.startsWith("eq.");
  });

  if (filterEntries.length === 0) return rows;

  return rows.filter((row) => {
    if (!row || typeof row !== "object") return false;
    return filterEntries.every(([key, value]) => {
      const expectedRaw = value.slice("eq.".length);
      if (!(key in row)) return false;
      const actual = (row as Record<string, unknown>)[key];
      if (actual === undefined) return false;
      if (typeof actual === "number") {
        const expectedNum = Number(expectedRaw);
        return Number.isNaN(expectedNum) ? false : actual === expectedNum;
      }
      if (typeof actual === "boolean") {
        if (expectedRaw === "true") return actual === true;
        if (expectedRaw === "false") return actual === false;
        return false;
      }
      if (typeof actual === "string") return actual === expectedRaw;
      return actual === expectedRaw;
    });
  });
}

function createMockFetch(state: SupabaseMockState): typeof fetch {
  return async (input, init) => {
    await Promise.resolve();
    const method = (
      init?.method ?? (input instanceof Request ? input.method : "GET")
    ).toUpperCase();
    const urlStr =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;

    const url = new URL(urlStr);
    state.requests.push({
      body: parseJsonBody(init?.body ?? null),
      method,
      url: `${url.pathname}${url.search}`,
    });

    if (url.pathname.startsWith("/rest/v1/")) {
      const headers = new Headers(init?.headers);
      const accept = headers.get("accept") ?? "";
      const wantsSingle = accept.includes("application/vnd.pgrst.object+json");
      const prefer = headers.get("prefer") ?? "";
      const resource = decodeURIComponent(url.pathname.replace("/rest/v1/", ""));

      if (resource.startsWith("rpc/")) {
        const fn = resource.slice("rpc/".length);
        const result = state.rpcResults.get(fn) ?? { data: null, error: null };
        if (result.error) {
          return jsonResponse(makePostgrestErrorPayload(result.error), { status: 400 });
        }
        const filtered = applyEqFilters(result.data, url.searchParams);
        const rows = wantsSingle
          ? Array.isArray(filtered)
            ? (filtered[0] ?? null)
            : filtered
          : filtered;
        const contentRange = makeContentRange(result.count, rows);
        return jsonResponse(rows ?? null, {
          headers: contentRange ? { "content-range": contentRange } : undefined,
          status: 200,
        });
      }

      if (method === "POST") {
        const forcedError = state.insertErrorsByTable.get(resource);
        if (forcedError) {
          return jsonResponse(makePostgrestErrorPayload(forcedError), { status: 400 });
        }
        const parsed = parseJsonBody(init?.body ?? null);
        const hydratedRows = hydrateInsertedRows(state, resource, parsed);
        if (parsed != null) {
          const byTable = state.insertByTable.get(resource) ?? [];
          byTable.push(...hydratedRows);
          state.insertByTable.set(resource, byTable);
          state.insertCapture.push(parsed);
        }
        if (prefer.includes("return=representation")) {
          return jsonResponse(wantsSingle ? (hydratedRows[0] ?? null) : hydratedRows, {
            status: 201,
          });
        }
        return jsonResponse([], { status: 201 });
      }

      if (method === "PATCH") {
        const parsed = parseJsonBody(init?.body ?? null);
        if (parsed != null) {
          const byTable = state.updateByTable.get(resource) ?? [];
          byTable.push(parsed);
          state.updateByTable.set(resource, byTable);
          state.updateCapture.push(parsed);
        }
        if (prefer.includes("return=representation")) {
          const rows = flattenInsertedRows(parsed);
          return jsonResponse(wantsSingle ? (rows[0] ?? null) : rows, { status: 200 });
        }
        return jsonResponse([], { status: 200 });
      }

      if (method === "DELETE") {
        const existingRows = state.insertByTable.get(resource) ?? [];
        const matched = applyEqFilters(existingRows, url.searchParams);
        const matchedRows = Array.isArray(matched) ? matched : [];

        if (matchedRows.length > 0) {
          const remaining = existingRows.filter((row) => !matchedRows.includes(row));
          state.insertByTable.set(resource, remaining);
        }

        const contentRange = makeContentRange(matchedRows.length, matchedRows);
        const body = prefer.includes("return=representation") ? matchedRows : [];
        return jsonResponse(body, {
          headers: contentRange ? { "content-range": contentRange } : undefined,
          status: 200,
        });
      }

      const select = state.selectByTable.get(resource) ?? state.selectResult;

      if (select.error) {
        return jsonResponse(makePostgrestErrorPayload(select.error), {
          status: 400,
        });
      }

      const limitParam = url.searchParams.get("limit");
      const offsetParam = url.searchParams.get("offset");
      const offset = offsetParam ? Number.parseInt(offsetParam, 10) : 0;
      const limit = limitParam ? Number.parseInt(limitParam, 10) : undefined;

      let resolvedData = select.data;
      if (select === state.selectResult) {
        const inserted = state.insertByTable.get(resource) ?? [];
        const insertedRows = inserted.flatMap(flattenInsertedRows);
        if (
          Array.isArray(resolvedData) &&
          resolvedData.length === 0 &&
          insertedRows.length > 0
        ) {
          resolvedData = insertedRows;
        }
      }

      resolvedData = applyEqFilters(resolvedData, url.searchParams);

      const slicedData =
        Array.isArray(resolvedData) && typeof limit === "number"
          ? resolvedData.slice(offset, offset + limit)
          : resolvedData;

      const rows = wantsSingle
        ? Array.isArray(slicedData)
          ? (slicedData[0] ?? null)
          : slicedData
        : slicedData;

      const contentRange = makeContentRange(select.count, rows);
      return jsonResponse(rows ?? null, {
        headers: contentRange ? { "content-range": contentRange } : undefined,
        status: 200,
      });
    }

    if (url.pathname.startsWith("/storage/v1/object/sign/")) {
      const parts = decodeURIComponent(
        url.pathname.replace("/storage/v1/object/sign/", "")
      )
        .split("/")
        .filter(Boolean);
      const bucket = parts[0] ?? "bucket";
      const token = state.storageToken;

      if (parts.length === 1) {
        const parsed = parseJsonBody(init?.body ?? null);
        const paths =
          parsed &&
          typeof parsed === "object" &&
          "paths" in parsed &&
          Array.isArray(parsed.paths)
            ? (parsed.paths as unknown[]).filter(
                (p): p is string => typeof p === "string"
              )
            : [];
        const payload = paths.map((path) => ({
          error: null,
          path,
          signedURL: `/object/sign/${bucket}/${path}?token=${token}`,
        }));
        return jsonResponse(payload, { status: 200 });
      }

      const path = parts.slice(1).join("/");
      return jsonResponse(
        { signedURL: `/object/sign/${bucket}/${path}?token=${token}` },
        {
          status: 200,
        }
      );
    }

    if (url.pathname.startsWith("/storage/v1/object/")) {
      const parts = decodeURIComponent(url.pathname.replace("/storage/v1/object/", ""))
        .split("/")
        .filter(Boolean);
      const bucket = parts[0] ?? "bucket";
      const path = parts.slice(1).join("/");
      return jsonResponse(
        { Id: "mock-storage-id", Key: `${bucket}/${path}` },
        { status: 200 }
      );
    }

    return jsonResponse({ message: "Mock endpoint not implemented" }, { status: 404 });
  };
}

export function getSupabaseMockState(
  client: SupabaseClient<Database>
): SupabaseMockState {
  const state = STATE.get(client);
  if (!state) {
    throw new Error("Supabase mock state not found for client instance");
  }
  return state;
}

export function resetSupabaseMockState(client: SupabaseClient<Database>): void {
  const state = getSupabaseMockState(client);
  state.autoIncrement.clear();
  state.insertCapture.length = 0;
  state.insertByTable.clear();
  state.insertErrorsByTable.clear();
  state.updateCapture.length = 0;
  state.updateByTable.clear();
  state.requests.length = 0;
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
): SupabaseClient<Database> => {
  const selectResult = config?.selectResult ?? { count: null, data: [], error: null };
  const normalizedUser =
    config?.user === undefined
      ? createMockUser()
      : config.user
        ? createMockUser(config.user)
        : null;

  const state: SupabaseMockState = {
    autoIncrement: new Map(),
    insertByTable: new Map(),
    insertCapture: config?.insertCapture ?? [],
    insertErrorsByTable: new Map(Object.entries(config?.insertErrors ?? {})),
    requests: [],
    rpcResults: new Map(Object.entries(config?.rpcResults ?? {})),
    selectByTable: new Map(Object.entries(config?.selectResults ?? {})),
    selectResult,
    storageToken: config?.storageToken ?? "abc",
    updateByTable: new Map(),
    updateCapture: config?.updateCapture ?? [],
    user: normalizedUser,
  };

  const supabaseUrl = "http://localhost:54321";
  const supabaseKey = "test-anon-key";

  const client = createClient<Database>(supabaseUrl, supabaseKey, {
    auth: {
      autoRefreshToken: false,
      detectSessionInUrl: false,
      persistSession: false,
    },
    global: {
      fetch: createMockFetch(state),
    },
    realtime: {
      params: { apikey: supabaseKey },
    },
  });

  STATE.set(client, state);

  vi.spyOn(client.auth, "getSession").mockImplementation(() => {
    if (state.user) {
      return Promise.resolve({
        data: { session: createMockSession(state.user) },
        error: null,
      });
    }
    return Promise.resolve({ data: { session: null }, error: null });
  });

  vi.spyOn(client.auth, "getUser").mockImplementation(() => {
    if (state.user) return Promise.resolve({ data: { user: state.user }, error: null });
    return Promise.resolve({
      data: { user: null },
      error: new AuthError("Not authenticated", 401, "no_authorization"),
    });
  });

  vi.spyOn(client.auth, "onAuthStateChange").mockImplementation((callback) => ({
    data: {
      subscription: {
        callback,
        id: "mock-subscription-id",
        unsubscribe: vi.fn(),
      },
    },
  }));

  vi.spyOn(client.auth, "signUp").mockImplementation(() => {
    if (state.user) {
      const nextSession = createMockSession(state.user);
      return Promise.resolve({
        data: { session: nextSession, user: state.user },
        error: null,
      });
    }
    return Promise.resolve({ data: { session: null, user: null }, error: null });
  });

  vi.spyOn(client.auth, "signInWithPassword").mockImplementation(() => {
    if (state.user) {
      const nextSession = createMockSession(state.user);
      return Promise.resolve({
        data: { session: nextSession, user: state.user },
        error: null,
      });
    }
    return Promise.resolve({
      data: { session: null, user: null, weakPassword: null },
      error: new AuthError("Invalid credentials", 400, "invalid_credentials"),
    });
  });

  vi.spyOn(client.auth, "signOut").mockResolvedValue({ error: null });

  vi.spyOn(client.auth, "resetPasswordForEmail").mockResolvedValue({
    data: {},
    error: null,
  });

  vi.spyOn(client.auth, "updateUser").mockImplementation(() => {
    if (state.user) return Promise.resolve({ data: { user: state.user }, error: null });
    return Promise.resolve({
      data: { user: null },
      error: new AuthError("Not authenticated", 401, "no_authorization"),
    });
  });

  vi.spyOn(client.auth, "signInWithOAuth").mockResolvedValue({
    data: { provider: "github", url: "" },
    error: null,
  });

  vi.spyOn(client.auth, "refreshSession").mockImplementation(() => {
    if (state.user) {
      const nextSession = createMockSession(state.user);
      return Promise.resolve({
        data: { session: nextSession, user: state.user },
        error: null,
      });
    }
    return Promise.resolve({ data: { session: null, user: null }, error: null });
  });

  const originalChannel = client.channel.bind(client);
  vi.spyOn(client, "channel").mockImplementation((name, opts) => {
    const channel = originalChannel(name, opts);
    vi.spyOn(channel, "on").mockImplementation(() => channel);
    vi.spyOn(channel, "subscribe").mockImplementation(() => channel);
    return channel;
  });

  return client;
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
    return Promise.resolve(client);
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

// Re-export test client utility for convenience
export { createTestBrowserClient } from "@/test/helpers/supabase-test-client";
