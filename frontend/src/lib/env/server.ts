/**
 * @fileoverview Server-only environment variable access.
 *
 * This module MUST only be imported in server contexts (API routes, Server
 * Components, server actions). It validates and caches server environment
 * variables at module load time.
 */

import "server-only";
import type { ServerEnv } from "./schema";
import { envSchema } from "./schema";

// Cached validated environment (parsed once at module load)
let cachedEnv: ServerEnv | null = null;
let validationError: Error | null = null;

/**
 * Parse and validate server environment variables.
 *
 * @throws Error if validation fails
 */
function validateServerEnv(): ServerEnv {
  if (cachedEnv) {
    return cachedEnv;
  }

  if (validationError) {
    throw validationError;
  }

  try {
    cachedEnv = envSchema.parse(process.env);
    return cachedEnv;
  } catch (error) {
    if (error instanceof Error && "issues" in error) {
      const zodError = error as { issues: Array<{ path: string[]; message: string }> };
      const errors = zodError.issues.map(
        (issue) => `${issue.path.join(".")}: ${issue.message}`
      );
      validationError = new Error(
        `Environment validation failed:\n${errors.join("\n")}`
      );
    } else {
      validationError =
        error instanceof Error ? error : new Error("Environment validation failed");
    }
    throw validationError;
  }
}

/**
 * Get validated server environment variables.
 *
 * @returns Validated server environment object
 * @throws Error if validation fails or called on client
 */
export function getServerEnv(): ServerEnv {
  // In test environments, window may be defined by the test runner
  // Check for actual browser context, not just window existence
  if (
    typeof window !== "undefined" &&
    typeof process !== "undefined" &&
    process.env.NODE_ENV !== "test"
  ) {
    throw new Error("getServerEnv() cannot be called on client side");
  }
  return validateServerEnv();
}

/**
 * Get a specific server environment variable by key.
 *
 * @param key - Environment variable key
 * @returns Environment variable value
 * @throws Error if key is missing or invalid
 */
export function getServerEnvVar<T extends keyof ServerEnv>(key: T): ServerEnv[T] {
  const env = getServerEnv();
  const value = env[key];
  if (value === undefined) {
    throw new Error(`Environment variable ${String(key)} is not defined`);
  }
  return value;
}

/**
 * Get server environment variable with fallback.
 *
 * @param key - Environment variable key
 * @param fallback - Fallback value if key is missing
 * @returns Environment variable value or fallback
 */
export function getServerEnvVarWithFallback<T extends keyof ServerEnv>(
  key: T,
  fallback: ServerEnv[T]
): ServerEnv[T] {
  try {
    return getServerEnvVar(key);
  } catch {
    return fallback;
  }
}

// Google Maps Platform helpers (server-only)
/**
 * Get Google Maps Platform server API key.
 *
 * Server key must be IP+API restricted for Places, Routes, Geocoding, Time Zone.
 *
 * @returns Server API key
 * @throws Error if key is missing or invalid
 */
export function getGoogleMapsServerKey(): string {
  const key = getServerEnvVar("GOOGLE_MAPS_SERVER_API_KEY");
  if (!key || key === "undefined") {
    throw new Error(
      "GOOGLE_MAPS_SERVER_API_KEY is required for Google Maps Platform services"
    );
  }
  return key;
}

// Export validated env object for advanced use cases (lazy getter)
let envCache: ServerEnv | null = null;
export const env = new Proxy({} as ServerEnv, {
  get(_target, prop) {
    if (!envCache) {
      envCache = getServerEnv();
    }
    return envCache[prop as keyof ServerEnv];
  },
  getOwnPropertyDescriptor(_target, prop) {
    if (!envCache) {
      envCache = getServerEnv();
    }
    return Object.getOwnPropertyDescriptor(envCache, prop);
  },
  ownKeys() {
    if (!envCache) {
      envCache = getServerEnv();
    }
    return Object.keys(envCache);
  },
});
