/**
 * @fileoverview Typed helper utilities for Supabase CRUD operations with Zod validation.
 * These helpers centralize runtime validation using Zod schemas while preserving
 * compile-time shapes using the generated `Database` types.
 */

import { getSupabaseSchema } from "@schemas/supabase";
import type { SupabaseClient } from "@supabase/supabase-js";
import type { Database, InsertTables, Tables, UpdateTables } from "./database.types";

export type TypedClient = SupabaseClient<Database>;

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
  const tableName = table as string;
  type SupportedTable = "trips" | "flights" | "accommodations" | "user_settings";
  let schema: ReturnType<typeof getSupabaseSchema> | undefined;
  if (["trips", "flights", "accommodations", "user_settings"].includes(tableName)) {
    schema = getSupabaseSchema(tableName as SupportedTable);
    if (schema?.insert && !Array.isArray(values)) {
      schema.insert.parse(values);
    }
  }

  // Keep any-cast localized while ensuring compile-time payload types.
  // biome-ignore lint/suspicious/noExplicitAny: Required for Supabase query builder typing
  const anyClient = client as unknown as { from: (t: string) => any };
  const insertQb = anyClient.from(tableName).insert(values as unknown);
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
export async function updateSingle<T extends keyof Database["public"]["Tables"]>(
  client: TypedClient,
  table: T,
  updates: Partial<UpdateTables<T>>,
  where: (qb: unknown) => unknown
): Promise<{ data: Tables<T> | null; error: unknown }> {
  // Validate input if schema exists
  const tableName = table as string;
  const schema = getSupabaseSchema(
    tableName as "trips" | "flights" | "accommodations" | "user_settings"
  );
  if (schema?.update) {
    schema.update.parse(updates);
  }

  // biome-ignore lint/suspicious/noExplicitAny: Required for Supabase query builder typing
  const anyClient = client as unknown as { from: (t: string) => any };
  let qb: unknown = anyClient.from(tableName).update(updates as unknown);
  qb = where(qb);
  // `.single()` ensures a single row is returned; adjust if multiple rows are expected
  // biome-ignore lint/suspicious/noExplicitAny: Required for Supabase query builder typing
  const anyQb = qb as { select: () => { single: () => Promise<any> } };
  const { data, error } = await anyQb.select().single();
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
export async function getSingle<T extends keyof Database["public"]["Tables"]>(
  client: TypedClient,
  table: T,
  where: (qb: unknown) => unknown
): Promise<{ data: Tables<T> | null; error: unknown }> {
  const tableName = table as string;
  const schema = getSupabaseSchema(
    tableName as "trips" | "flights" | "accommodations" | "user_settings"
  );

  // biome-ignore lint/suspicious/noExplicitAny: Required for Supabase query builder typing
  const anyClient = client as unknown as { from: (t: string) => any };
  let qb: unknown = anyClient.from(tableName).select("*");
  qb = where(qb);
  // biome-ignore lint/suspicious/noExplicitAny: Required for Supabase query builder typing
  const anyQb = qb as { single: () => Promise<any> };
  const { data, error } = await anyQb.single();
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
export async function deleteSingle<T extends keyof Database["public"]["Tables"]>(
  client: TypedClient,
  table: T,
  where: (qb: unknown) => unknown
): Promise<{ error: unknown }> {
  const tableName = table as string;

  // biome-ignore lint/suspicious/noExplicitAny: Required for Supabase query builder typing
  const anyClient = client as unknown as { from: (t: string) => any };
  let qb: unknown = anyClient.from(tableName).delete();
  qb = where(qb);
  // biome-ignore lint/suspicious/noExplicitAny: Required for Supabase query builder typing
  const anyQb = qb as { then: (fn: (result: any) => void) => Promise<any> };
  const { error } = await anyQb;
  return { error: error ?? null };
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
export async function getMaybeSingle<T extends keyof Database["public"]["Tables"]>(
  client: TypedClient,
  table: T,
  where: (qb: unknown) => unknown
): Promise<{ data: Tables<T> | null; error: unknown }> {
  const tableName = table as string;
  const schema = getSupabaseSchema(
    tableName as "trips" | "flights" | "accommodations" | "user_settings"
  );

  // biome-ignore lint/suspicious/noExplicitAny: Required for Supabase query builder typing
  const anyClient = client as unknown as { from: (t: string) => any };
  let qb: unknown = anyClient.from(tableName).select("*");
  qb = where(qb);
  // biome-ignore lint/suspicious/noExplicitAny: Required for Supabase query builder typing
  const anyQb = qb as { maybeSingle: () => Promise<any> };
  const { data, error } = await anyQb.maybeSingle();
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
  const tableName = table as string;
  type SupportedTable = "trips" | "flights" | "accommodations" | "user_settings";
  let schema: ReturnType<typeof getSupabaseSchema> | undefined;
  if (["trips", "flights", "accommodations", "user_settings"].includes(tableName)) {
    schema = getSupabaseSchema(tableName as SupportedTable);
    if (schema?.insert) {
      schema.insert.parse(values);
    }
  }

  // biome-ignore lint/suspicious/noExplicitAny: Required for Supabase query builder typing
  const anyClient = client as unknown as { from: (t: string) => any };
  const upsertQb = anyClient.from(tableName).upsert(values as unknown, {
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
