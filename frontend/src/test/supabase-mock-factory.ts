/**
 * @fileoverview Reusable Supabase mock factory for tests.
 *
 * Provides a flexible mock factory that accepts configuration for insert
 * capture and select results, making tests resilient to internal query changes.
 */

import type { TypedServerSupabase } from "@/lib/supabase/server";

/**
 * Configuration for Supabase mock factory.
 */
export interface SupabaseMockConfig {
  /**
   * Array to capture insert payloads.
   * All insert operations will push their payloads to this array.
   */
  insertCapture: unknown[];

  /**
   * Result to return from select queries.
   * Supports async single() queries that return { data, error }.
   */
  selectResult?: {
    data: unknown;
    error: unknown;
  };
}

/**
 * Creates a mock Supabase client factory for testing.
 *
 * Returns a function that creates a mock Supabase client with:
 * - `from(table)` method that returns insert/select builders
 * - `insert()` that captures payloads to insertCapture array
 * - `select()` that returns a chainable query builder ending in single()
 *
 * @param config - Configuration for insert capture and select results
 * @returns Async function that returns a mock TypedServerSupabase client
 *
 * @example
 * ```typescript
 * const insertCapture: unknown[] = [];
 * const supabase = createMockSupabase({
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
export function createMockSupabase(
  config: SupabaseMockConfig
): () => Promise<TypedServerSupabase> {
  const { insertCapture, selectResult = { data: null, error: null } } = config;

  return async () =>
    ({
      from: (_table: string) => ({
        insert: (payload: unknown) => {
          insertCapture.push(payload);
          return Promise.resolve({ error: null });
        },
        select: () => ({
          eq: () => ({
            eq: () => ({
              single: async () => ({
                data: selectResult.data,
                error: selectResult.error,
              }),
            }),
          }),
        }),
      }),
    }) as unknown as TypedServerSupabase;
}
