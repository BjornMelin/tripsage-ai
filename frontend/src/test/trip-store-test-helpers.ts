/**
 * @fileoverview Helpers for mocking Supabase trip CRUD flows in store tests.
 */

import { randomInt, randomUUID } from "node:crypto";
import type { SupabaseClient } from "@supabase/supabase-js";
import { vi } from "vitest";

type TripTableName = "trips";

interface TripRow {
  id: number;
  uuid_id: string;
  user_id: string;
  title: string;
  name: string;
  description: string;
  start_date: string | null;
  end_date: string | null;
  destination: string | null;
  budget: number | null;
  currency: string;
  spent_amount: number;
  visibility: "private" | "public";
  tags: string[];
  preferences: Record<string, unknown>;
  status: string;
  budget_breakdown: Record<string, unknown> | null;
  created_at: string;
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

const globalMockData: Record<TripTableName, TripRow[]> = {
  trips: [],
};

const toTripRow = (input: TripInsert): TripRow => {
  const now = new Date().toISOString();

  return {
    id: Number(Date.now() + randomInt(0, 1000)),
    uuid_id: randomUUID(),
    user_id: "test-user-id",
    title: input.title ?? input.name ?? "Untitled Trip",
    name: input.name ?? input.title ?? "Untitled Trip",
    description: input.description ?? "",
    start_date: input.startDate ?? null,
    end_date: input.endDate ?? null,
    destination: typeof input.destinations === "string" ? input.destinations : null,
    budget: input.budget ?? null,
    currency: input.currency ?? "USD",
    spent_amount: 0,
    visibility: input.isPublic ? "public" : "private",
    tags: [],
    preferences: {},
    status: "planning",
    budget_breakdown: null,
    created_at: now,
    updated_at: now,
  };
};

const applyFilters = (rows: TripRow[], filters: TripFilter[]): TripRow[] =>
  filters.reduce<TripRow[]>(
    (acc, filter) => acc.filter((row) => row[filter.column] === filter.value),
    rows
  );

class TripQueryBuilder implements PromiseLike<{ data: TripRow[]; error: null }> {
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
    this.insertedRows = rows.map(toTripRow);
    globalMockData[this.table].push(...this.insertedRows);
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

  async single() {
    if (this.operation === "insert" && this.insertedRows.length === 1) {
      return { data: this.insertedRows[0], error: null };
    }

    const tableData = [...globalMockData[this.table]];
    const filtered = this.filters.length
      ? applyFilters(tableData, this.filters)
      : tableData;

    if (this.operation === "update" && filtered[0] && this.updatePatch) {
      const updated: TripRow = {
        ...filtered[0],
        ...this.updatePatch,
        updated_at: new Date().toISOString(),
      };
      const index = tableData.findIndex((row) => row.id === filtered[0].id);
      if (index >= 0) {
        globalMockData[this.table][index] = updated;
      }
      return { data: updated, error: null };
    }

    if (this.operation === "delete" && filtered[0]) {
      const remaining = tableData.filter((row) => row.id !== filtered[0].id);
      globalMockData[this.table] = remaining;
      return { data: filtered[0], error: null };
    }

    return { data: filtered[0] ?? null, error: null };
  }

  maybeSingle() {
    return this.single();
  }

  then<TResult1 = { data: TripRow[]; error: null }, TResult2 = never>(
    onFulfilled?:
      | ((value: { data: TripRow[]; error: null }) => TResult1 | PromiseLike<TResult1>)
      | null
      | undefined,
    onRejected?:
      | ((reason: unknown) => TResult2 | PromiseLike<TResult2>)
      | null
      | undefined
  ) {
    if (this.operation === "select") {
      const rows = this.filters.length
        ? applyFilters(globalMockData[this.table], this.filters)
        : globalMockData[this.table];
      return Promise.resolve({ data: rows, error: null }).then(onFulfilled, onRejected);
    }
    return Promise.resolve({ data: [] as TripRow[], error: null }).then(
      onFulfilled,
      onRejected
    );
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
          user: { id: "test-user-id" },
          access_token: "test-token",
        },
      },
      error: null,
    })),
    onAuthStateChange: vi.fn(() => ({
      data: { subscription: { unsubscribe: vi.fn() } },
    })),
    signUp: vi.fn(async () => ({ data: null, error: null })),
    signInWithPassword: vi.fn(async () => ({ data: null, error: null })),
    signOut: vi.fn(async () => ({ error: null })),
    resetPasswordForEmail: vi.fn(async () => ({ data: null, error: null })),
    updateUser: vi.fn(async () => ({ data: null, error: null })),
  } as unknown as SupabaseClient<unknown>["auth"],
  from: vi.fn((table: string) => {
    if (table !== "trips") {
      throw new Error(`Unsupported table ${table} in trip store mock`);
    }
    return new TripQueryBuilder("trips");
  }) as unknown as SupabaseClient<unknown>["from"],
  channel: vi.fn(() => ({
    on: vi.fn().mockReturnThis(),
    subscribe: vi.fn(() => ({ unsubscribe: vi.fn() })),
  })) as unknown as SupabaseClient<unknown>["channel"],
  removeChannel: vi.fn(),
});

/** Reset the shared trip data between tests. */
export const resetTripStoreMockData = () => {
  globalMockData.trips = [];
};

/** Pre-populate the trip table with deterministic entries. */
export const populateTripStoreMockData = (rows: TripRow[]): void => {
  globalMockData.trips = [...rows];
};
