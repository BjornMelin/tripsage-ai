import { randomInt, randomUUID } from "node:crypto";
import type { SupabaseClient } from "@supabase/supabase-js";
import { vi } from "vitest";

type TripTableName = "trips";

interface TripRow {
  id: number;
  // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
  uuid_id: string;
  // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
  user_id: string;
  title: string;
  name: string;
  description: string;
  // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
  start_date: string | null;
  // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
  end_date: string | null;
  destination: string | null;
  budget: number | null;
  currency: string;
  // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
  spent_amount: number;
  visibility: "private" | "public";
  tags: string[];
  preferences: Record<string, unknown>;
  status: string;
  // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
  budget_breakdown: Record<string, unknown> | null;
  // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
  created_at: string;
  // biome-ignore lint/style/useNamingConvention: Database column names use snake_case
  updated_at: string;
}

type TripInsert = Partial<TripRow> & {
  name?: string;
  title?: string;
  startDate?: string;
  endDate?: string;
  currency?: string;
  budget?: number;
  description?: string;
  destinations?: unknown;
  isPublic?: boolean;
};

interface TripFilter {
  column: keyof TripRow;
  value: TripRow[keyof TripRow] | null;
}

const GLOBAL_MOCK_DATA: Record<TripTableName, TripRow[]> = {
  trips: [],
};

const TO_TRIP_ROW = (input: TripInsert): TripRow => {
  const now = new Date().toISOString();

  return {
    budget: input.budget ?? null,
    budget_breakdown: null,
    created_at: now,
    currency: input.currency ?? "USD",
    description: input.description ?? "",
    destination: typeof input.destinations === "string" ? input.destinations : null,
    end_date: input.endDate ?? null,
    id: Number(Date.now() + randomInt(0, 1000)),
    name: input.name ?? input.title ?? "Untitled Trip",
    preferences: {},
    spent_amount: 0,
    start_date: input.startDate ?? null,
    status: "planning",
    tags: [],
    title: input.title ?? input.name ?? "Untitled Trip",
    updated_at: now,
    user_id: "test-user-id",
    uuid_id: randomUUID(),
    visibility: input.isPublic ? "public" : "private",
  };
};

const APPLY_FILTERS = (rows: TripRow[], filters: TripFilter[]): TripRow[] =>
  filters.reduce<TripRow[]>(
    (acc, filter) => acc.filter((row) => row[filter.column] === filter.value),
    rows
  );

class TripQueryBuilder {
  private operation: "select" | "insert" | "update" | "delete" | null = null;
  private filters: TripFilter[] = [];
  private insertedRows: TripRow[] = [];
  private updatePatch: Partial<TripRow> | null = null;

  constructor(private readonly table: TripTableName) {}

  select(): this {
    this.operation = "select";
    return this;
  }

  insert(rows: TripInsert[]): this {
    this.operation = "insert";
    this.insertedRows = rows.map(TO_TRIP_ROW);
    GLOBAL_MOCK_DATA[this.table].push(...this.insertedRows);
    return this;
  }

  update(patch: Partial<TripRow>): this {
    this.operation = "update";
    this.updatePatch = patch;
    return this;
  }

  delete(): this {
    this.operation = "delete";
    return this;
  }

  eq(column: keyof TripRow, value: TripRow[keyof TripRow] | null): this {
    this.filters.push({ column, value });
    return this;
  }

  order(): this {
    return this;
  }

  range(): this {
    return this;
  }

  single() {
    if (this.operation === "insert" && this.insertedRows.length === 1) {
      return { data: this.insertedRows[0], error: null };
    }

    const tableData = [...GLOBAL_MOCK_DATA[this.table]];
    const filtered = this.filters.length
      ? APPLY_FILTERS(tableData, this.filters)
      : tableData;

    if (this.operation === "update" && filtered[0] && this.updatePatch) {
      const updated: TripRow = {
        ...filtered[0],
        ...this.updatePatch,
        updated_at: new Date().toISOString(),
      };
      const index = tableData.findIndex((row) => row.id === filtered[0].id);
      if (index >= 0) {
        GLOBAL_MOCK_DATA[this.table][index] = updated;
      }
      return { data: updated, error: null };
    }

    if (this.operation === "delete" && filtered[0]) {
      const remaining = tableData.filter((row) => row.id !== filtered[0].id);
      GLOBAL_MOCK_DATA[this.table] = remaining;
      return { data: filtered[0], error: null };
    }

    return { data: filtered[0] ?? null, error: null };
  }

  maybeSingle() {
    return this.single();
  }
}

/**
 * Create a Supabase client mock tailored for trip store tests.
 * @returns Partial SupabaseClient with typed trip table helpers.
 */
export const createTripStoreMockClient = (): Partial<SupabaseClient<unknown>> => ({
  auth: {
    getSession: vi.fn(async () => ({
      data: {
        session: {
          access_token: "test-token",
          user: { id: "test-user-id" },
        },
      },
      error: null,
    })),
    onAuthStateChange: vi.fn(() => ({
      data: { subscription: { unsubscribe: vi.fn() } },
    })),
    resetPasswordForEmail: vi.fn(async () => ({ data: null, error: null })),
    signInWithPassword: vi.fn(async () => ({ data: null, error: null })),
    signOut: vi.fn(async () => ({ error: null })),
    signUp: vi.fn(async () => ({ data: null, error: null })),
    updateUser: vi.fn(async () => ({ data: null, error: null })),
  } as unknown as SupabaseClient<unknown>["auth"],
  channel: vi.fn(() => ({
    on: vi.fn().mockReturnThis(),
    subscribe: vi.fn(() => ({ unsubscribe: vi.fn() })),
  })) as unknown as SupabaseClient<unknown>["channel"],
  from: vi.fn((table: string) => {
    if (table !== "trips") {
      throw new Error(`Unsupported table ${table} in trip store mock`);
    }
    return new TripQueryBuilder("trips");
  }) as unknown as SupabaseClient<unknown>["from"],
  removeChannel: vi.fn(),
});

/** Reset the shared trip data between tests. */
export const resetTripStoreMockData = () => {
  GLOBAL_MOCK_DATA.trips = [];
};

/** Pre-populate the trip table with deterministic entries. */
export const populateTripStoreMockData = (rows: TripRow[]): void => {
  GLOBAL_MOCK_DATA.trips = [...rows];
};
