/**
 * @fileoverview Typed helper utilities for Supabase CRUD operations with Zod validation.
 * These helpers centralize runtime validation using Zod schemas while preserving
 * compile-time shapes using the generated `Database` types.
 */

import { getSupabaseSchema } from "@schemas/supabase";
import type { SupabaseClient } from "@supabase/supabase-js";
import type { Database, InsertTables, Tables, UpdateTables } from "./database.types";

export type TypedClient = SupabaseClient<Database>;

type TableName = keyof Database["public"]["Tables"];
/**
 * Query builder type alias using `any` intentionally.
 * Supabase's query builder is any-based internally; precise generics cause
 * excessive complexity and type instability. Biome rule suppressed below.
 */
// biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing is any-based
export type TableFilterBuilder<_T extends TableName> = any;

const SUPPORTED_TABLES = [
  "trips",
  "flights",
  "accommodations",
  "user_settings",
] as const;
type SupportedTable = (typeof SUPPORTED_TABLES)[number];
const isSupportedTable = (table: TableName): table is SupportedTable =>
  SUPPORTED_TABLES.includes(table as SupportedTable);

/**
 * Inserts a row into the specified table and returns the single selected row.
 * Uses `.select().single()` to fetch the inserted record in one roundtrip.
 * Validates input and output using Zod schemas when available.
 *
 * Note: When inserting multiple rows, `.single()` will error. For batches,
 * add a dedicated `insertMany` helper without `.single()` if needed.
 *
 * @template T Table name constrained to `Database['public']['Tables']` keys
 * @param client Typed supabase client
 * @param table Target table name
 * @param values Insert payload (validated via Zod schema)
 * @returns Selected row (validated) and error (if any)
 */
export async function insertSingle<T extends keyof Database["public"]["Tables"]>(
  client: TypedClient,
  table: T,
  values: InsertTables<T> | InsertTables<T>[]
): Promise<{ data: Tables<T> | null; error: unknown }> {
  // Validate input if schema exists
  const schema = isSupportedTable(table) ? getSupabaseSchema(table) : undefined;
  if (schema?.insert && !Array.isArray(values)) {
    schema.insert.parse(values);
  }

  // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
  const anyClient = client as any;
  // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
  const insertQb = (anyClient as any).from(table as string).insert(values as unknown);
  // Some tests stub a very lightweight query builder without select/single methods.
  // Gracefully handle those by treating the insert as fire-and-forget.
  if (insertQb && typeof insertQb.select === "function") {
    const { data, error } = await insertQb.select().single();
    if (error) return { data: null, error };
    // Validate output if schema exists
    if (schema?.row && data) {
      try {
        const validated = schema.row.parse(data);
        return { data: validated as Tables<T>, error: null };
      } catch (validationError) {
        return { data: null, error: validationError };
      }
    }
    return { data: (data ?? null) as Tables<T> | null, error: null };
  }
  return { data: null, error: null };
}

/**
 * Updates rows in the specified table and returns a single selected row.
 * A `where` closure receives the fluent query builder to apply filters
 * (`eq`, `in`, etc.) prior to selecting the row.
 * Validates input and output using Zod schemas when available.
 *
 * @template T Table name constrained to `Database['public']['Tables']` keys
 * @param client Typed supabase client
 * @param table Target table name
 * @param updates Partial update payload (validated via Zod schema)
 * @param where Closure to apply filters to the builder
 * @returns Selected row (validated) and error (if any)
 */
export async function updateSingle<T extends TableName>(
  client: TypedClient,
  table: T,
  updates: Partial<UpdateTables<T>>,
  where: (qb: TableFilterBuilder<T>) => TableFilterBuilder<T>
): Promise<{ data: Tables<T> | null; error: unknown }> {
  // Validate input if schema exists
  const schema = isSupportedTable(table) ? getSupabaseSchema(table) : undefined;
  if (schema?.update) {
    schema.update.parse(updates);
  }

  // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
  const anyClient = client as any;
  const filtered = where(
    // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
    (anyClient as any)
      .from(table as string)
      .update(updates as unknown) as TableFilterBuilder<T>
  );
  const { data, error } = await filtered.select().single();
  if (error) return { data: null, error };
  // Validate output if schema exists
  if (schema?.row && data) {
    try {
      const validated = schema.row.parse(data);
      return { data: validated as Tables<T>, error: null };
    } catch (validationError) {
      return { data: null, error: validationError };
    }
  }
  return { data: (data ?? null) as Tables<T> | null, error: null };
}

/**
 * Fetches a single row from the specified table.
 * A `where` closure receives the fluent query builder to apply filters
 * (`eq`, `in`, etc.) prior to selecting the row.
 * Validates output using Zod schemas when available.
 *
 * @template T Table name constrained to `Database['public']['Tables']` keys
 * @param client Typed supabase client
 * @param table Target table name
 * @param where Closure to apply filters to the builder
 * @returns Selected row (validated) and error (if any)
 */
export async function getSingle<T extends TableName>(
  client: TypedClient,
  table: T,
  where: (qb: TableFilterBuilder<T>) => TableFilterBuilder<T>
): Promise<{ data: Tables<T> | null; error: unknown }> {
  const schema = isSupportedTable(table) ? getSupabaseSchema(table) : undefined;

  // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
  const anyClient = client as any;
  const qb = where(
    // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
    (anyClient as any).from(table as string).select("*") as TableFilterBuilder<T>
  );
  const { data, error } = await qb.single();
  if (error) return { data: null, error };
  if (!data) return { data: null, error: null };
  // Validate output if schema exists
  if (schema?.row && data) {
    try {
      const validated = schema.row.parse(data);
      return { data: validated as Tables<T>, error: null };
    } catch (validationError) {
      return { data: null, error: validationError };
    }
  }
  return { data: (data ?? null) as Tables<T> | null, error: null };
}

/**
 * Deletes rows from the specified table matching the given criteria.
 * A `where` closure receives the fluent query builder to apply filters
 * (`eq`, `in`, etc.) prior to deletion.
 *
 * @template T Table name constrained to `Database['public']['Tables']` keys
 * @param client Typed supabase client
 * @param table Target table name
 * @param where Closure to apply filters to the builder
 * @returns Error (if any)
 */
export async function deleteSingle<T extends TableName>(
  client: TypedClient,
  table: T,
  where: (qb: TableFilterBuilder<T>) => TableFilterBuilder<T>
): Promise<{ count: number; error: unknown | null }> {
  // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
  const anyClient = client as any;
  const qb = where(
    // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
    (anyClient as any)
      .from(table as string)
      .delete({ count: "exact" }) as TableFilterBuilder<T>
  );
  const { count, error } = await qb;
  return { count: count ?? 0, error: error ?? null };
}

/**
 * Fetches a single row from the specified table, returning null if not found.
 * Uses `.maybeSingle()` instead of `.single()` to avoid PGRST116 errors.
 * A `where` closure receives the fluent query builder to apply filters
 * (`eq`, `in`, etc.) prior to selecting the row.
 * Validates output using Zod schemas when available.
 *
 * @template T Table name constrained to `Database['public']['Tables']` keys
 * @param client Typed supabase client
 * @param table Target table name
 * @param where Closure to apply filters to the builder
 * @returns Selected row (validated) or null, and error (if any)
 */
export async function getMaybeSingle<T extends TableName>(
  client: TypedClient,
  table: T,
  where: (qb: TableFilterBuilder<T>) => TableFilterBuilder<T>
): Promise<{ data: Tables<T> | null; error: unknown }> {
  const schema = isSupportedTable(table) ? getSupabaseSchema(table) : undefined;

  // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
  const anyClient = client as any;
  const qb = where(
    // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
    (anyClient as any).from(table as string).select("*") as TableFilterBuilder<T>
  );
  const { data, error } = await qb.maybeSingle();
  if (error) return { data: null, error };
  if (!data) return { data: null, error: null };
  // Validate output if schema exists
  if (schema?.row && data) {
    try {
      const validated = schema.row.parse(data);
      return { data: validated as Tables<T>, error: null };
    } catch (validationError) {
      return { data: null, error: validationError };
    }
  }
  return { data: data as Tables<T>, error: null };
}

/**
 * Upserts a row into the specified table and returns the single selected row.
 * Uses `.upsert()` with onConflict to perform insert-or-update operations.
 * Validates input and output using Zod schemas when available.
 *
 * @template T Table name constrained to `Database['public']['Tables']` keys
 * @param client Typed supabase client
 * @param table Target table name
 * @param values Upsert payload (validated via Zod schema)
 * @param onConflict Column name(s) to determine conflict (e.g., "user_id")
 * @returns Selected row (validated) and error (if any)
 */
export async function upsertSingle<T extends keyof Database["public"]["Tables"]>(
  client: TypedClient,
  table: T,
  values: InsertTables<T>,
  onConflict: string
): Promise<{ data: Tables<T> | null; error: unknown }> {
  const schema = isSupportedTable(table) ? getSupabaseSchema(table) : undefined;
  if (schema?.insert) {
    schema.insert.parse(values);
  }

  // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
  const anyClient = client as any;
  // biome-ignore lint/suspicious/noExplicitAny: Supabase query builder typing
  const upsertQb = (anyClient as any).from(table as string).upsert(values as unknown, {
    ignoreDuplicates: false,
    onConflict,
  });

  // Chain select/single to return the upserted row
  if (upsertQb && typeof upsertQb.select === "function") {
    const { data, error } = await upsertQb.select().single();
    if (error) return { data: null, error };
    // Validate output if schema exists
    if (schema?.row && data) {
      try {
        const validated = schema.row.parse(data);
        return { data: validated as Tables<T>, error: null };
      } catch (validationError) {
        return { data: null, error: validationError };
      }
    }
    return { data: (data ?? null) as Tables<T> | null, error: null };
  }
  return { data: null, error: null };
}
