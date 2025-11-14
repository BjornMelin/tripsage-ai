/**
 * @fileoverview Test helpers for stubbing environment variables and controlling module reloads.
 */

import { vi } from "vitest";

/**
 * Disables Upstash rate limiting by not providing environment values.
 */
export function stubRateLimitDisabled(): void {
  // Don't set UPSTASH vars - absence disables rate limiting
  // (empty strings would fail URL validation)
  // Provide minimal Supabase env to satisfy server env validation in routes
  vi.stubEnv?.("NEXT_PUBLIC_SUPABASE_URL", "https://test.supabase.co");
  vi.stubEnv?.("NEXT_PUBLIC_SUPABASE_ANON_KEY", "anon-test-key");
  vi.stubEnv?.("SUPABASE_SERVICE_ROLE_KEY", "srk-test-key");
}

/**
 * Enables Upstash rate limiting by stubbing placeholder environment values.
 */
export function stubRateLimitEnabled(): void {
  vi.stubEnv?.("UPSTASH_REDIS_REST_URL", "https://example.upstash.io");
  vi.stubEnv?.("UPSTASH_REDIS_REST_TOKEN", "test-token");
  // Provide minimal Supabase env to satisfy server env validation in routes
  vi.stubEnv?.("NEXT_PUBLIC_SUPABASE_URL", "https://test.supabase.co");
  vi.stubEnv?.("NEXT_PUBLIC_SUPABASE_ANON_KEY", "anon-test-key");
  vi.stubEnv?.("SUPABASE_SERVICE_ROLE_KEY", "srk-test-key");
}

/**
 * Resets modules to force module-scope code to re-run and then imports a path.
 *
 * @param path - Module path to import after resetting modules.
 * @returns Promise resolving to the imported module.
 */
export async function resetAndImport<T = unknown>(path: string): Promise<T> {
  vi.resetModules();
  return (await import(path)) as unknown as T;
}

/**
 * Best-effort unstubbing of all environment variables for older/newer Vitest versions.
 */
export function unstubAllEnvs(): void {
  try {
    vi.unstubAllEnvs?.();
  } catch {
    // no-op on older versions
  }
}
