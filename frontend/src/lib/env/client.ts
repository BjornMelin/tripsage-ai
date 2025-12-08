/**
 * @fileoverview Client-safe environment variable access.
 *
 * This module exports only NEXT_PUBLIC_* environment variables that are
 * safe to expose in client bundles. All values are validated at build time
 * and frozen to prevent mutation.
 */

import type { ClientEnv } from "@schemas/env";
import { clientEnvSchema } from "@schemas/env";

/**
 * Extract and validate client-safe environment variables.
 *
 * @returns Validated client environment object
 * @throws Error if validation fails
 */
function validateClientEnv(): ClientEnv {
  // Extract NEXT_PUBLIC_ variables from process.env
  const clientVars = Object.fromEntries(
    Object.entries(process.env).filter(([key]) => key.startsWith("NEXT_PUBLIC_"))
  );

  try {
    return clientEnvSchema.parse(clientVars);
  } catch (error) {
    if (error instanceof Error && "issues" in error) {
      const zodError = error as { issues: Array<{ path: string[]; message: string }> };
      const errors = zodError.issues.map(
        (issue) => `${issue.path.join(".")}: ${issue.message}`
      );

      // In development, log but don't throw to allow graceful degradation
      if (process.env.NODE_ENV === "development") {
        console.error(`Client environment validation failed:\n${errors.join("\n")}`);
        // Return partial object with defaults for development
        return {
          NEXT_PUBLIC_APP_NAME: "TripSage",
          NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT: "http://localhost:4318/v1/traces",
          NEXT_PUBLIC_SUPABASE_ANON_KEY: "",
          NEXT_PUBLIC_SUPABASE_URL: "",
        };
      }

      throw new Error(`Client environment validation failed:\n${errors.join("\n")}`);
    }
    throw error;
  }
}

// Validate and freeze client environment at module load
const publicEnvValue = Object.freeze(validateClientEnv());

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
