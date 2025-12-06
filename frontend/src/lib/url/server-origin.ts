/**
 * @fileoverview Server-side URL origin resolution utilities.
 *
 * Provides safe origin resolution for server actions and API routes.
 * Prevents SSRF by using trusted environment variables instead of user input.
 */

import "server-only";

import { getServerEnvVarWithFallback } from "@/lib/env/server";
import { createServerLogger } from "@/lib/telemetry/logger";

/**
 * Default localhost origin for development environments.
 *
 * WARNING: This fallback should only be used in development. In production,
 * ensure APP_BASE_URL or NEXT_PUBLIC_SITE_URL is set to prevent SSRF risks
 * from misconfigured environments. The localhost fallback is acceptable for
 * local development but must not be used in production deployments.
 */
const DEFAULT_LOCALHOST_ORIGIN = "http://localhost:3000";

/**
 * Whether the application is running in production mode.
 */
const isProduction = process.env.NODE_ENV === "production";

const logger = createServerLogger("url.server-origin");

function resolveConfiguredOrigin(): string | null {
  try {
    const appBaseUrl = getServerEnvVarWithFallback("APP_BASE_URL", "");
    if (appBaseUrl && typeof appBaseUrl === "string" && appBaseUrl.trim().length > 0) {
      return appBaseUrl;
    }
  } catch {
    // APP_BASE_URL not available, continue to next option
  }

  try {
    const siteUrl = getServerEnvVarWithFallback("NEXT_PUBLIC_SITE_URL", "");
    if (siteUrl && typeof siteUrl === "string" && siteUrl.trim().length > 0) {
      return siteUrl;
    }
  } catch {
    // NEXT_PUBLIC_SITE_URL not available, continue to next option
  }

  const baseUrl = process.env.NEXT_PUBLIC_BASE_URL;
  if (baseUrl && typeof baseUrl === "string" && baseUrl.trim().length > 0) {
    return baseUrl;
  }

  return null;
}

/**
 * Resolves the application origin for server-side requests.
 *
 * Uses environment variables in priority order; in production, missing configuration
 * will throw to avoid silently using localhost.
 */
export function getServerOrigin(): string {
  const origin = resolveConfiguredOrigin();
  if (origin) return origin;

  logger.warn("server origin not configured - using localhost:3000 fallback", {
    environment: process.env.NODE_ENV,
    hint: "Set APP_BASE_URL or NEXT_PUBLIC_SITE_URL",
  });

  return DEFAULT_LOCALHOST_ORIGIN;
}

/**
 * Resolves the application origin for server-side requests.
 * Throws an error in production if no valid origin is configured.
 *
 * Use this variant for critical operations (payments, webhooks) where
 * falling back to localhost would cause silent failures.
 *
 * @returns Application origin URL
 * @throws {Error} In production if no origin is configured
 */
export function getRequiredServerOrigin(): string {
  const origin = resolveConfiguredOrigin();
  if (origin) return origin;

  logger.error("required server origin missing", {
    hint: "Set APP_BASE_URL or NEXT_PUBLIC_SITE_URL",
  });

  if (isProduction) {
    throw new Error(
      "Server origin not configured. Set APP_BASE_URL or NEXT_PUBLIC_SITE_URL environment variable."
    );
  }

  logger.warn("required server origin missing - using localhost:3000 for development");
  return DEFAULT_LOCALHOST_ORIGIN;
}

/**
 * Converts a relative path to an absolute URL using the server origin.
 *
 * If the path is already absolute (starts with http:// or https://), returns it as-is.
 * Otherwise, resolves it relative to the server origin.
 *
 * @param path - Relative or absolute path/URL
 * @returns Absolute URL
 */
export function toAbsoluteUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  const origin = getServerOrigin();
  return new URL(path, origin).toString();
}
