/**
 * @fileoverview Helpers for Next.js Route Handlers (headers/ratelimit identifiers).
 */

import { createHash } from "node:crypto";
import { type NextRequest, NextResponse } from "next/server";
import type { z } from "zod";

type ValidationIssue = z.core.$ZodIssue;

/**
 * Shared API constants used across route handlers.
 */
export const API_CONSTANTS = {
  /** Content-Type for JSON responses */
  jsonContentType: "application/json",
  /** Maximum request body size for API endpoints (64KB) */
  maxBodySizeBytes: 64 * 1024,
} as const;

/**
 * Extract the client IP from trusted sources with deterministic fallback.
 *
 * Priority order:
 * 1. req.ip (Next.js 16+ trusted IP from Vercel/proxy)
 * 2. x-vercel-ip header (Vercel-specific trusted IP)
 * 3. x-forwarded-for header (first IP, caller-controlled)
 * 4. x-real-ip header (caller-controlled)
 * 5. "unknown" (fallback when no IP available)
 *
 * The fallback of "unknown" avoids undefined identifiers when rate limiting.
 *
 * @param req Next.js request object.
 * @returns Client IP string or "unknown".
 */
export function getClientIpFromHeaders(req: NextRequest): string {
  // Prefer Vercel-specific trusted header
  const headers = req.headers;
  const vercelIp = headers.get("x-vercel-ip");
  if (vercelIp && vercelIp.length > 0) {
    return vercelIp.trim();
  }

  // Fallback to proxy headers (caller-controlled, less trusted)
  const xff = headers.get("x-forwarded-for");
  if (xff && xff.length > 0) {
    const firstIp = xff.split(",")[0]?.trim();
    if (firstIp) return firstIp;
  }

  const real = headers.get("x-real-ip");
  if (real && real.length > 0) {
    return real.trim();
  }

  return "unknown";
}

/**
 * Hash an identifier for use in rate limiting to prevent enumeration attacks.
 *
 * Uses SHA-256 and returns a hex string. This prevents attackers from
 * enumerating rate limit buckets by guessing identifiers.
 *
 * @param identifier Raw identifier string.
 * @returns Hashed identifier as hex string.
 */
export function hashIdentifier(identifier: string): string {
  return createHash("sha256").update(identifier).digest("hex");
}

/**
 * Get a trusted, hashed identifier for rate limiting.
 *
 * Extracts the client IP using trusted sources and hashes it to prevent
 * enumeration attacks. Falls back to "unknown" when no IP is available.
 *
 * @param req Next.js request object.
 * @returns Hashed identifier string.
 */
export function getTrustedRateLimitIdentifier(req: NextRequest): string {
  const ip = getClientIpFromHeaders(req);
  // Hash to prevent enumeration; "unknown" remains "unknown" after hashing
  if (ip === "unknown") {
    return "unknown";
  }
  return hashIdentifier(ip);
}

/**
 * Redact sensitive fields from error messages and context objects.
 *
 * Prevents secrets from appearing in logs by replacing sensitive values
 * with "[REDACTED]".
 *
 * @param error Error object or message string.
 * @param context Optional context object to sanitize.
 * @returns Sanitized error message and context.
 */
export function redactErrorForLogging(
  error: unknown,
  context?: Record<string, unknown>
): { message: string; context?: Record<string, unknown> } {
  const message =
    error instanceof Error ? error.message : String(error ?? "Unknown error");

  // Redact common sensitive patterns in error messages
  const redactedMessage = message
    .replace(/sk-[a-zA-Z0-9]{20,}/g, "[REDACTED]")
    .replace(/api[_-]?key["\s:=]+([a-zA-Z0-9_-]{10,})/gi, 'api_key="[REDACTED]"')
    .replace(/token["\s:=]+([a-zA-Z0-9_-]{10,})/gi, 'token="[REDACTED]"')
    .replace(/secret["\s:=]+([a-zA-Z0-9_-]{10,})/gi, 'secret="[REDACTED]"');

  const redactedContext = context
    ? Object.entries(context).reduce<Record<string, unknown>>((acc, [key, value]) => {
        const keyLower = key.toLowerCase();
        if (
          keyLower.includes("key") ||
          keyLower.includes("token") ||
          keyLower.includes("secret") ||
          keyLower.includes("password") ||
          keyLower.includes("auth")
        ) {
          acc[key] = "[REDACTED]";
        } else {
          acc[key] = value;
        }
        return acc;
      }, {})
    : undefined;

  return { context: redactedContext, message: redactedMessage };
}

/**
 * Return the Authorization header value if present.
 */
export function getAuthorization(req: NextRequest): string | null {
  return req.headers.get("authorization");
}

/**
 * Build a stable rate-limit identifier using bearer token (if any) and client IP.
 */
export function buildRateLimitKey(req: NextRequest): string {
  const auth = getAuthorization(req) || "anon";
  const bearer = auth.startsWith("Bearer ") ? auth.slice(7) : auth;
  const ip = getClientIpFromHeaders(req);
  return `${bearer}:${ip}`;
}

/**
 * Forward safe headers to a backend call. Currently forwards only Authorization.
 */
export function forwardAuthHeaders(req: NextRequest): HeadersInit | undefined {
  const auth = getAuthorization(req);
  // biome-ignore lint/style/useNamingConvention: HTTP headers conventionally use PascalCase
  return auth ? { Authorization: auth } : undefined;
}

/**
 * Result of authentication check.
 */
export interface AuthCheckResult {
  user: unknown; // Supabase User type
  error: unknown; // Supabase AuthError type
  isAuthenticated: boolean;
}

/**
 * Perform standardized authentication check with Supabase.
 *
 * @param supabase - Supabase client instance
 * @returns Authentication check result
 */
export async function checkAuthentication(
  supabase: unknown // SupabaseClient type
): Promise<AuthCheckResult> {
  const { data, error } = await (
    supabase as {
      auth: { getUser: () => Promise<{ data: { user: unknown }; error: unknown }> };
    }
  ).auth.getUser();
  const user = data?.user;
  const isAuthenticated = !error && !!user;

  return {
    error,
    isAuthenticated,
    user,
  };
}

/**
 * Wrap a function execution with a request span for observability.
 *
 * Records duration and attributes for telemetry. Uses high-resolution time
 * for accurate measurements.
 *
 * @param name - Span name for identification.
 * @param attrs - Attributes to include in the span log.
 * @param f - Function to execute and measure.
 * @returns Promise resolving to the function's return value.
 */
export async function withRequestSpan<T>(
  name: string,
  attrs: Record<string, string | number>,
  f: () => Promise<T>
): Promise<T> {
  const start = process.hrtime.bigint();
  try {
    return await f();
  } finally {
    const end = process.hrtime.bigint();
    const durationMs = Number(end - start) / 1e6;
    console.debug("agent.span", {
      durationMs,
      name,
      ...attrs,
    });
  }
}

/**
 * Create a standardized error response for agent routes.
 *
 * Returns a NextResponse with consistent error shape and sanitized logging.
 * All errors are logged with redaction to prevent secrets leakage.
 *
 * @param opts - Error response options.
 * @param opts.status - HTTP status code.
 * @param opts.error - Error code string (e.g., "invalid_request", "rate_limit_exceeded").
 * @param opts.reason - Human-readable reason string.
 * @param opts.err - Optional error object to log (will be redacted).
 * @returns NextResponse with standardized error format.
 */
export function errorResponse({
  err,
  error,
  reason,
  status,
  issues,
}: {
  error: string;
  reason: string;
  status: number;
  err?: unknown;
  issues?: ValidationIssue[];
}): NextResponse {
  if (err) {
    const { context, message } = redactErrorForLogging(err);
    console.error("agent.error", { context, error, message, reason });
  }
  const body: {
    error: string;
    reason: string;
    issues?: ValidationIssue[];
  } = {
    error,
    reason,
  };

  if (issues) {
    body.issues = issues;
  }

  return NextResponse.json(body, { status });
}
