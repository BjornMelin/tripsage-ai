/**
 * @fileoverview Server-only validated environment access with per-process caching and build-phase fail-fast guard.
 */

import "server-only";
import type { ServerEnv } from "@schemas/env";
import { envSchema } from "@schemas/env";
import { isBuildPhase } from "@/lib/utils/build-phase";

// Single cached validated environment
let envCache: ServerEnv | null = null;
let parseError: Error | null = null;

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
 * Detects obviously placeholder values that should not be used as real keys.
 * Common placeholder patterns: "your-*", "changeme*", "*placeholder*", "*example*".
 *
 * @param value - Trimmed env var value
 * @returns true if the value looks like a placeholder and should be ignored
 */
function isPlaceholderValue(value: string): boolean {
  const lower = value.toLowerCase();
  // Common placeholder patterns from .env.example templates
  if (
    lower.startsWith("your-") ||
    lower.startsWith("your_") ||
    lower.startsWith("changeme") ||
    lower.includes("placeholder") ||
    lower.includes("example") ||
    lower === "your-publishable-key" ||
    lower === "your-anon-key"
  ) {
    return true;
  }
  return false;
}

function createBuildPhaseServerEnvProxy(): ServerEnv {
  const handler: ProxyHandler<ServerEnv> = {
    get(_target, prop) {
      if (typeof prop === "string") {
        throw new Error(
          `Server env ${prop} accessed during Next.js build phase. Guard access with isBuildPhase() or provide runtime env vars.`
        );
      }
      return undefined as never;
    },
  };
  return new Proxy({} as ServerEnv, handler);
}

/** Test-only helper to clear cached env between runs. */
export function __resetServerEnvCacheForTest() {
  envCache = null;
  parseError = null;
}

function parseServerEnv(): ServerEnv {
  if (envCache) {
    return envCache;
  }
  if (parseError) {
    throw parseError;
  }

  // During build phase, always return a Proxy that fails fast on access.
  if (isBuildPhase()) {
    envCache = createBuildPhaseServerEnvProxy();
    return envCache;
  }

  try {
    const envForParse = { ...process.env };

    // Supabase renamed "anon" to "publishable" keys; support both to reduce DX drift.
    // Prefer publishable key when available, but ignore obvious placeholder values.
    const publishableKey = normalizeOptionalEnvVar(
      envForParse.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
    );
    const anonKey = normalizeOptionalEnvVar(envForParse.NEXT_PUBLIC_SUPABASE_ANON_KEY);

    // Use publishable key only if it's not a placeholder; otherwise fall back to anon key
    const resolvedSupabaseKey =
      publishableKey && !isPlaceholderValue(publishableKey)
        ? publishableKey
        : anonKey && !isPlaceholderValue(anonKey)
          ? anonKey
          : undefined;

    if (resolvedSupabaseKey) {
      envForParse.NEXT_PUBLIC_SUPABASE_ANON_KEY = resolvedSupabaseKey;
    }

    const nodeEnvRaw =
      normalizeOptionalEnvVar(envForParse.NODE_ENV) ??
      normalizeOptionalEnvVar(process.env.NODE_ENV) ??
      "development";
    const isProduction = nodeEnvRaw === "production";

    /**
     * In non-production, tolerate obviously invalid placeholder values for optional
     * env vars so the dev server can boot without requiring every integration to be
     * configured.
     *
     * Production remains strict and will still fail fast for misconfiguration.
     */
    function deleteIfInvalidNonProd(
      key: keyof NodeJS.ProcessEnv,
      isInvalid: (value: string) => boolean
    ) {
      if (isProduction) return;
      const rawValue = envForParse[key];
      const value = normalizeOptionalEnvVar(rawValue);
      if (!value) {
        // Some schemas (e.g., z.url().optional()) cannot accept empty strings; treat
        // empty/undefined placeholders as "unset" in non-production.
        if (rawValue !== undefined) {
          Reflect.deleteProperty(envForParse, key);
        }
        return;
      }
      if (isInvalid(value) || isPlaceholderValue(value)) {
        Reflect.deleteProperty(envForParse, key);
      }
    }

    deleteIfInvalidNonProd(
      "QSTASH_CURRENT_SIGNING_KEY",
      (value) => value !== "" && value.length < 32
    );
    deleteIfInvalidNonProd(
      "QSTASH_NEXT_SIGNING_KEY",
      (value) => value !== "" && value.length < 32
    );
    deleteIfInvalidNonProd(
      "QSTASH_TOKEN",
      (value) => value !== "" && value.length < 20
    );
    deleteIfInvalidNonProd("COLLAB_WEBHOOK_URL", (value) => {
      try {
        new URL(value);
        return false;
      } catch {
        return true;
      }
    });

    envCache = envSchema.parse(envForParse);
    return envCache;
  } catch (error) {
    if (error instanceof Error && "issues" in error) {
      const zodError = error as { issues: Array<{ path: string[]; message: string }> };
      const messages = zodError.issues.map(
        (issue) => `${issue.path.join(".")}: ${issue.message}`
      );
      parseError = new Error(`Environment validation failed:\n${messages.join("\n")}`);
    } else {
      parseError =
        error instanceof Error ? error : new Error("Environment validation failed");
    }
    throw parseError;
  }
}

/**
 * Get validated server environment variables.
 *
 * @returns Validated server environment object
 * @throws Error if validation fails or called on client
 */
export function getServerEnv(): ServerEnv {
  if (typeof window !== "undefined") {
    throw new Error("getServerEnv() cannot be called on client side");
  }

  return parseServerEnv();
}

/**
 * Get a specific server environment variable by key.
 *
 * @param key - Environment variable key
 * @returns Environment variable value
 * @throws Error if key is missing or invalid
 */
export function getServerEnvVar<T extends keyof ServerEnv>(
  key: T
): Exclude<ServerEnv[T], undefined> {
  const env = getServerEnv();
  const value = env[key];
  if (value === undefined) {
    throw new Error(`Environment variable ${String(key)} is not defined`);
  }
  return value as Exclude<ServerEnv[T], undefined>;
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
  try {
    const key = getServerEnvVar("GOOGLE_MAPS_SERVER_API_KEY");
    if (!key || key === "undefined") {
      throw new Error(
        "GOOGLE_MAPS_SERVER_API_KEY is required for Google Maps Platform services"
      );
    }
    return key;
  } catch (error) {
    // When the env var is missing entirely, preserve original 'not defined' message
    if (error instanceof Error && error.message.includes("not defined")) {
      throw error;
    }
    throw error instanceof Error
      ? error
      : new Error(
          "GOOGLE_MAPS_SERVER_API_KEY is required for Google Maps Platform services"
        );
  }
}

/**
 * Get the public Google Maps browser key from a server context.
 *
 * This key is safe to embed in client-consumed URLs and should be referrer-restricted.
 *
 * @returns Public browser key or undefined if unavailable (or during build phase)
 */
export function getGoogleMapsBrowserKey(): string | undefined {
  if (isBuildPhase()) return undefined;
  const key = getServerEnvVarWithFallback(
    "NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY",
    undefined
  );
  if (!key || key === "undefined") return undefined;
  return key;
}

// Export validated env object for advanced use cases (lazy getter)
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
