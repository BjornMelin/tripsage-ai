/**
 * @fileoverview Client-safe origin resolution helpers.
 */

import { getClientEnvVarWithFallback } from "@/lib/env/client";

const DEFAULT_LOCALHOST_ORIGIN = "http://localhost:3000";
const isProduction = process.env.NODE_ENV === "production";

/**
 * Resolves the application origin for client-side contexts.
 *
 * Prefers browser location, then trusted public env vars.
 */
export function getClientOrigin(): string {
  if (typeof window !== "undefined" && typeof window.location?.origin === "string") {
    return window.location.origin;
  }

  const siteUrl = getClientEnvVarWithFallback("NEXT_PUBLIC_SITE_URL", "");
  if (siteUrl) {
    return siteUrl;
  }

  const baseUrl = getClientEnvVarWithFallback("NEXT_PUBLIC_BASE_URL", "");
  if (baseUrl) {
    return baseUrl;
  }

  const appUrl = getClientEnvVarWithFallback("NEXT_PUBLIC_APP_URL", "");
  if (appUrl) {
    return appUrl;
  }

  if (!isProduction && typeof window !== "undefined") {
    // Dev-only nudge to configure site/base URL; avoids server-side console usage
    console.warn(
      "[client-origin] No NEXT_PUBLIC_SITE_URL or NEXT_PUBLIC_BASE_URL configured. Falling back to http://localhost:3000"
    );
  }

  return DEFAULT_LOCALHOST_ORIGIN;
}

/**
 * Converts a relative path to an absolute URL using the client origin.
 */
export function toClientAbsoluteUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  return new URL(path, getClientOrigin()).toString();
}
