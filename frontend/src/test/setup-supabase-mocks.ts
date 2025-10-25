/**
 * @fileoverview Setup file for Supabase mocks used in tests.
 */

import { vi } from "vitest";
import { createMockSupabaseClient } from "./mock-helpers";

// Mock environment variables
vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://test.supabase.co");
vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "test-anon-key");

/**
 * Gets a mock Supabase client for testing.
 * @return A mock Supabase client instance.
 */
const getMockSupabaseClient = () => createMockSupabaseClient();

export { getMockSupabaseClient };
