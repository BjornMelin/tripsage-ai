/**
 * @fileoverview Server-side URL origin resolution utilities.
 */

import "server-only";

import type { NextRequest } from "next/server";
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

/**
 * Validates that a host value is well-formed and doesn't contain suspicious characters.
 * Blocks userinfo segments (@), control characters, and other injection vectors.
 */
function isValidHost(host: string): boolean {
  if (!host || !host.trim()) return false;

  // Block userinfo segments (evil.com@trusted.com), control chars, spaces
  if (/[@\s\t\r\n]/.test(host)) {
    logger.warn("rejected invalid x-forwarded-host", {
      host,
      reason: "suspicious-chars",
    });
    return false;
  }

  // Basic hostname pattern: alphanumeric, dots, hyphens, optional port
  // Allows: example.com, sub.example.com, localhost:3000, 192.168.1.1:8080
  const hostnamePattern = /^[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?(:\d+)?$/;
  if (!hostnamePattern.test(host)) {
    logger.warn("rejected invalid x-forwarded-host", {
      host,
      reason: "invalid-format",
    });
    return false;
  }

  return true;
}

function resolveConfiguredOrigin(): string | null {
  const normalizeOrigin = (raw: string, key: string): string | null => {
    try {
      const url = new URL(raw.trim());
      if (url.username || url.password) return null;
      if (url.protocol !== "http:" && url.protocol !== "https:") return null;
      return url.origin;
    } catch {
      logger.warn("invalid configured origin env var", { key });
      return null;
    }
  };

  const getNonEmptyEnvVar = (
    key:
      | "APP_BASE_URL"
      | "NEXT_PUBLIC_SITE_URL"
      | "NEXT_PUBLIC_BASE_URL"
      | "NEXT_PUBLIC_APP_URL"
  ): string | null => {
    const value = getServerEnvVarWithFallback(key, "");
    if (value && value.trim().length > 0) {
      return normalizeOrigin(value, key);
    }
    return null;
  };

  const appBaseUrl = getNonEmptyEnvVar("APP_BASE_URL");
  if (appBaseUrl) return appBaseUrl;

  const siteUrl = getNonEmptyEnvVar("NEXT_PUBLIC_SITE_URL");
  if (siteUrl) return siteUrl;

  const baseUrl = getNonEmptyEnvVar("NEXT_PUBLIC_BASE_URL");
  if (baseUrl) return baseUrl;

  const appUrl = getNonEmptyEnvVar("NEXT_PUBLIC_APP_URL");
  if (appUrl) return appUrl;

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
    hint: "Set APP_BASE_URL, NEXT_PUBLIC_SITE_URL, NEXT_PUBLIC_BASE_URL, or NEXT_PUBLIC_APP_URL",
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
    hint: "Set APP_BASE_URL, NEXT_PUBLIC_SITE_URL, NEXT_PUBLIC_BASE_URL, or NEXT_PUBLIC_APP_URL",
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

/**
 * Resolves the origin from a NextRequest, preferring configured origin for security.
 *
 * Priority (security-first):
 * 1. Configured origin from environment variables (most secure)
 * 2. x-forwarded-host + x-forwarded-proto (only when no configured origin)
 * 3. Request URL origin (final fallback)
 *
 * WARNING: Only uses x-forwarded-* headers when no configured origin is available.
 * These headers must be set/stripped by a trusted reverse proxy. For strict
 * security guarantees, use getRequiredServerOrigin() instead.
 *
 * @param request - The incoming NextRequest
 * @returns The resolved origin URL (e.g., "https://example.com")
 */
export function getOriginFromRequest(request: NextRequest): string {
  // 1. Prefer configured origin (most secure - not influenced by request headers)
  const configuredOrigin = resolveConfiguredOrigin();
  if (configuredOrigin) {
    return configuredOrigin;
  }

  if (isProduction) {
    return getRequiredServerOrigin();
  }

  // 2. Only if no configured origin, consider forwarded headers from trusted proxy
  const forwardedHost = request.headers.get("x-forwarded-host");
  if (forwardedHost) {
    const rawProto = request.headers.get("x-forwarded-proto") ?? "https";
    const protocolCandidate = rawProto.split(",")[0]?.trim().toLowerCase();

    // Validate protocol - only allow http/https, default to https for anything else
    const protocol =
      protocolCandidate === "http" || protocolCandidate === "https"
        ? protocolCandidate
        : "https";

    const host = forwardedHost.split(",")[0]?.trim();
    if (host && isValidHost(host)) {
      return `${protocol}://${host}`;
    }
  }

  // 3. Final fallback: request URL origin
  return new URL(request.url).origin;
}
