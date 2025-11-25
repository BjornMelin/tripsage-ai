/**
 * @fileoverview Server-side URL origin resolution utilities.
 *
 * Provides safe origin resolution for server actions and API routes.
 * Prevents SSRF by using trusted environment variables instead of user input.
 */

import "server-only";

import { getServerEnvVarWithFallback } from "@/lib/env/server";

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
 * Resolves the application origin for server-side requests.
 *
 * Uses environment variables in priority order:
 * 1. APP_BASE_URL (server-only, most trusted)
 * 2. NEXT_PUBLIC_SITE_URL (public but trusted)
 * 3. NEXT_PUBLIC_BASE_URL (fallback)
 * 4. localhost:3000 (development default - PRODUCTION: Ensure env vars are set)
 *
 * @returns Application origin URL
 */
export function getServerOrigin(): string {
  // Try APP_BASE_URL first (server-only, most trusted)
  try {
    const appBaseUrl = getServerEnvVarWithFallback("APP_BASE_URL", "");
    if (appBaseUrl && typeof appBaseUrl === "string" && appBaseUrl.trim().length > 0) {
      return appBaseUrl;
    }
  } catch {
    // APP_BASE_URL not available, continue to next option
  }

  // Try NEXT_PUBLIC_SITE_URL (public but trusted)
  try {
    const siteUrl = getServerEnvVarWithFallback("NEXT_PUBLIC_SITE_URL", "");
    if (siteUrl && typeof siteUrl === "string" && siteUrl.trim().length > 0) {
      return siteUrl;
    }
  } catch {
    // NEXT_PUBLIC_SITE_URL not available, continue to next option
  }

  // Try NEXT_PUBLIC_BASE_URL (fallback) - access via process.env since it's public
  const baseUrl = process.env.NEXT_PUBLIC_BASE_URL;
  if (baseUrl && typeof baseUrl === "string" && baseUrl.trim().length > 0) {
    return baseUrl;
  }

  // PRODUCTION: Ensure APP_BASE_URL is set to prevent localhost fallback
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
