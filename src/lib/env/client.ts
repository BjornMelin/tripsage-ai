/**
 * @fileoverview Client-safe environment variable access.
 */

import type { ClientEnv } from "@schemas/env";
import { clientEnvSchema } from "@schemas/env";
import { isBuildPhase } from "@/lib/utils/build-phase";

/**
 * Normalize an optional environment variable by trimming and removing falsy values.
 *
 * Treats `undefined`, empty strings, and the string "undefined" (case-insensitive,
 * e.g., "undefined", "UNDEFINED", "Undefined") as absent. This prevents drift
 * between environment configuration and runtime behavior.
 *
 * @param value - Raw environment variable value (may be undefined or whitespace)
 * @returns Trimmed value or undefined if empty/falsy
 */
function normalizeOptionalEnvVar(value: string | undefined): string | undefined {
  if (value === undefined) {
    return undefined;
  }
  const trimmed = value.trim();
  if (!trimmed || trimmed.toLowerCase() === "undefined") {
    return undefined;
  }
  return trimmed;
}

/**
 * Extract and validate client-safe environment variables.
 *
 * @returns Validated client environment object
 * @throws Error if validation fails (except during build/development)
 */
function validateClientEnv(): ClientEnv {
  // Avoid enumerating process.env in client bundles; Next.js inlines env var
  // accesses but does not guarantee process.env is enumerable in the browser.
  const resolvedSupabaseKey =
    normalizeOptionalEnvVar(process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY) ??
    normalizeOptionalEnvVar(process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY);

  const clientVars = {
    NEXT_PUBLIC_API_URL: normalizeOptionalEnvVar(process.env.NEXT_PUBLIC_API_URL),
    NEXT_PUBLIC_APP_NAME: normalizeOptionalEnvVar(process.env.NEXT_PUBLIC_APP_NAME),
    NEXT_PUBLIC_BASE_PATH: normalizeOptionalEnvVar(process.env.NEXT_PUBLIC_BASE_PATH),
    NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY: normalizeOptionalEnvVar(
      process.env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY
    ),
    NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT: normalizeOptionalEnvVar(
      process.env.NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT
    ),
    NEXT_PUBLIC_SITE_URL: normalizeOptionalEnvVar(process.env.NEXT_PUBLIC_SITE_URL),
    NEXT_PUBLIC_SUPABASE_ANON_KEY: resolvedSupabaseKey,
    NEXT_PUBLIC_SUPABASE_URL: normalizeOptionalEnvVar(
      process.env.NEXT_PUBLIC_SUPABASE_URL
    ),
  };

  try {
    return clientEnvSchema.parse(clientVars);
  } catch (error) {
    if (error instanceof Error && "issues" in error) {
      const zodError = error as { issues: Array<{ path: string[]; message: string }> };
      const errors = zodError.issues.map(
        (issue) => `${issue.path.join(".")}: ${issue.message}`
      );

      const allowPlaceholderPublicEnv =
        process.env.NODE_ENV === "development" ||
        (isBuildPhase() && process.env.NEXT_PUBLIC_ALLOW_PLACEHOLDER_ENV === "true");

      // Only allow placeholder NEXT_PUBLIC_* values in development, or when explicitly
      // opted-in during build (e.g. docs/CI builds). NEXT_PUBLIC_* values are inlined
      // into client bundles at build time.
      if (allowPlaceholderPublicEnv) {
        // Return partial object with defaults for development/build
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
