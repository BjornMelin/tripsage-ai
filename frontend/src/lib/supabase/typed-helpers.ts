/**
 * @fileoverview Typed helper utilities for Supabase CRUD operations.
 * These helpers centralize the minimal runtime casts required by the
 * PostgREST client while preserving compile-time shapes using the
 * generated `Database` types. Prefer these over ad‑hoc `(supabase as any)`.
 */

import type { SupabaseClient } from "@supabase/supabase-js";
import type { Database, InsertTables, Tables, UpdateTables } from "./database.types";

export type TypedClient = SupabaseClient<Database>;

/**
 * Inserts a row into the specified table and returns the single selected row.
 * Uses `.select().single()` to fetch the inserted record in one roundtrip.
 *
 * Note: When inserting multiple rows, `.single()` will error. For batches,
 * add a dedicated `insertMany` helper without `.single()` if needed.
 *
 * @template T Table name constrained to `Database['public']['Tables']` keys
 * @param client Typed supabase client
 * @param table Target table name
 * @param values Insert payload
 * @returns >} Selected row and error (if any)
 */
export async function insertSingle<T extends keyof Database["public"]["Tables"]>(
  client: TypedClient,
  table: T,
  values: InsertTables<T> | InsertTables<T>[]
): Promise<{ data: Tables<T> | null; error: unknown }> {
  // Keep any-cast localized while ensuring compile-time payload types.
  // biome-ignore lint/suspicious/noExplicitAny: Required for Supabase query builder typing
  const anyClient = client as unknown as { from: (t: string) => any };
  const { data, error } = await anyClient
    .from(table as string)
    .insert(values as unknown)
    .select()
    .single();
  return { data: (data ?? null) as Tables<T> | null, error };
}

/**
 * Updates rows in the specified table and returns a single selected row.
 * A `where` closure receives the fluent query builder to apply filters
 * (`eq`, `in`, etc.) prior to selecting the row.
 *
 * @template T Table name constrained to `Database['public']['Tables']` keys
 * @param client Typed supabase client
 * @param table Target table name
 * @param updates Partial update payload
 * @param where Closure to apply filters to the builder
 * @returns >} Selected row and error (if any)
 */
export async function updateSingle<T extends keyof Database["public"]["Tables"]>(
  client: TypedClient,
  table: T,
  updates: Partial<UpdateTables<T>>,
  where: (qb: unknown) => unknown
): Promise<{ data: Tables<T> | null; error: unknown }> {
  // biome-ignore lint/suspicious/noExplicitAny: Required for Supabase query builder typing
  const anyClient = client as unknown as { from: (t: string) => any };
  let qb: unknown = anyClient.from(table as string).update(updates as unknown);
  qb = where(qb);
  // `.single()` ensures a single row is returned; adjust if multiple rows are expected
  // biome-ignore lint/suspicious/noExplicitAny: Required for Supabase query builder typing
  const anyQb = qb as { select: () => { single: () => Promise<any> } };
  const { data, error } = await anyQb.select().single();
  return { data: (data ?? null) as Tables<T> | null, error };
}
