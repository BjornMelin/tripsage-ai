/**
 * @fileoverview Test utility for isolated Supabase browser clients.
 */

import { createBrowserClient } from "@supabase/ssr";
import type { Database } from "@/lib/supabase/database.types";

/**
 * Creates an isolated browser client for testing.
 * Uses `isSingleton: false` to prevent state leakage between tests.
 *
 * This is useful for integration tests that need a fresh client instance
 * without shared state from previous tests.
 *
 * @returns An isolated Supabase browser client
 */
export function createTestBrowserClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "http://localhost:54321";
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "test-anon-key";

  return createBrowserClient<Database>(url, key, {
    isSingleton: false,
  });
}
