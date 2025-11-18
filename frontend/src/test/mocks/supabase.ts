/**
 * @fileoverview Supabase client mocks for tests.
 * Use this in tests that need Supabase client functionality.
 */

import { vi } from "vitest";
import { createMockSupabaseClient } from "../mock-helpers";

/**
 * Sets up Supabase client mocks for a test file.
 * Call this at the top level of test files that use Supabase.
 *
 * @example
 * ```ts
 * import { setupSupabaseMocks } from "@/test/mocks/supabase";
 * setupSupabaseMocks();
 * ```
 */
export function setupSupabaseMocks() {
  const MOCK_SUPABASE = createMockSupabaseClient();

  vi.mock("@/lib/supabase", () => ({
    createClient: () => MOCK_SUPABASE,
    getBrowserClient: () => MOCK_SUPABASE,
    useSupabase: () => MOCK_SUPABASE,
  }));
}
