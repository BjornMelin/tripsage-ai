/**
 * @fileoverview Client-safe environment variable access.
 *
 * This module exports only NEXT_PUBLIC_* environment variables that are
 * safe to expose in client bundles. All values are validated at build time
 * and frozen to prevent mutation.
 */

import type { ClientEnv } from "./schema";
import { parseClientEnv } from "./schema";

/**
 * Extract and validate client-safe environment variables.
 *
 * Uses the centralized parseClientEnv() from schema with enhanced error handling
 * and graceful degradation in development environments. Returns a deeply frozen
 * object to prevent mutation at any level.
 *
 * @returns Validated and deeply frozen client environment object
 * @throws {EnvValidationError} If validation fails in production
 */
function validateClientEnv(): ClientEnv {
  return parseClientEnv(); // Already returns deeply frozen object
}

// Validate and freeze client environment at module load (parseClientEnv already deep-freezes)
const publicEnvValue = validateClientEnv();

/**
 * Get validated client environment variables.
 *
 * @returns Frozen client environment object
 */
export function getClientEnv(): ClientEnv {
  return publicEnvValue;
}

/**
 * Get a specific client environment variable by key.
 *
 * @param key - Environment variable key (must be NEXT_PUBLIC_*)
 * @returns Environment variable value
 * @throws Error if key is missing or invalid
 */
export function getClientEnvVar<T extends keyof ClientEnv>(key: T): ClientEnv[T] {
  const value = publicEnvValue[key];
  if (value === undefined) {
    throw new Error(`Client environment variable ${String(key)} is not defined`);
  }
  return value;
}

/**
 * Get client environment variable with fallback.
 *
 * @param key - Environment variable key
 * @param fallback - Fallback value if key is missing
 * @returns Environment variable value or fallback
 */
export function getClientEnvVarWithFallback<T extends keyof ClientEnv>(
  key: T,
  fallback: ClientEnv[T]
): ClientEnv[T] {
  const value = publicEnvValue[key];
  return value !== undefined ? value : fallback;
}

// Google Maps Platform helpers (client-safe)
/**
 * Get Google Maps Platform browser API key.
 *
 * Browser key must be HTTP referrer-restricted to Maps JS only.
 *
 * @returns Browser API key or undefined if not configured
 */
export function getGoogleMapsBrowserKey(): string | undefined {
  return publicEnvValue.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY;
}

// Export frozen public env object for convenience
export const publicEnv = publicEnvValue;
