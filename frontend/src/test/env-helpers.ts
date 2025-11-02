/**
 * @fileoverview Test helpers for stubbing environment variables and controlling module reloads.
 */

import { vi } from "vitest";

/**
 * Disables Upstash rate limiting by stubbing empty environment values.
 */
export function stubRateLimitDisabled(): void {
  // Empty strings prevent ratelimiter construction in route modules
  (vi as any).stubEnv?.("UPSTASH_REDIS_REST_URL", "");
  (vi as any).stubEnv?.("UPSTASH_REDIS_REST_TOKEN", "");
}

/**
 * Enables Upstash rate limiting by stubbing placeholder environment values.
 */
export function stubRateLimitEnabled(): void {
  (vi as any).stubEnv?.("UPSTASH_REDIS_REST_URL", "https://example.upstash.io");
  (vi as any).stubEnv?.("UPSTASH_REDIS_REST_TOKEN", "test-token");
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
    (vi as any).unstubAllEnvs?.();
  } catch {
    // no-op on older versions
  }
}
