/**
 * @fileoverview Server-side safe redirect URL resolver for auth flows.
 *
 * Prevents open-redirect attacks by validating redirect paths and
 * computing origins from configured environment variables or request context.
 */

import "server-only";

import type { NextRequest } from "next/server";
import { createServerLogger } from "@/lib/telemetry/logger";
import { getOriginFromRequest } from "@/lib/url/server-origin";

const FALLBACK_PATH = "/dashboard";

const logger = createServerLogger("auth.redirect-server");

/**
 * Logs a blocked redirect attempt and returns the fallback path.
 */
function rejectPath(reason: string, original: string): string {
  logger.warn("blocked unsafe redirect path", { original, reason });
  return FALLBACK_PATH;
}

/**
 * Validates and normalizes a redirect path to prevent open-redirect attacks.
 *
 * Only allows:
 * - Relative paths starting with "/" (e.g., "/dashboard", "/settings")
 *
 * Blocks:
 * - Protocol-relative URLs (e.g., "//evil.com")
 * - Absolute URLs with protocols (e.g., "https://evil.com")
 * - Empty or whitespace-only paths
 *
 * @param nextParam - The "next" query parameter value
 * @returns A safe relative path (always starts with "/")
 */
export function safeNextPath(nextParam: string | null | undefined): string {
  if (!nextParam) return FALLBACK_PATH;

  const trimmed = nextParam.trim();
  if (!trimmed) return FALLBACK_PATH;

  // Block protocol-relative URLs (//evil.com)
  if (trimmed.startsWith("//")) {
    return rejectPath("protocol-relative", trimmed);
  }

  // Block absolute URLs with protocols
  if (trimmed.includes("://")) {
    return rejectPath("absolute-url", trimmed);
  }

  // Only allow paths starting with /
  if (!trimmed.startsWith("/")) {
    return rejectPath("missing-leading-slash", trimmed);
  }

  // Normalize backslashes to forward slashes (Windows path injection)
  const normalized = trimmed.replace(/\\/g, "/");

  // Re-check after normalization for // patterns
  if (normalized.startsWith("//")) {
    return rejectPath("normalized-protocol-relative", trimmed);
  }

  // Validate path doesn't contain encoded protocol patterns.
  // Note: Only a single decode is intentional - double-encoded patterns like
  // /%252F remain encoded after this check, and browsers won't double-decode,
  // so they're safe. Infrastructure that double-decodes is a separate concern.
  try {
    const decoded = decodeURIComponent(normalized);
    if (decoded.startsWith("//") || decoded.includes("://")) {
      return rejectPath("encoded-protocol-pattern", trimmed);
    }
  } catch {
    // Invalid encoding - treat as safe since browser won't decode it either
  }

  return normalized;
}

/**
 * Resolves a full redirect URL for auth callbacks.
 *
 * Combines origin detection (respecting x-forwarded-* headers) with
 * safe path validation to produce a secure redirect URL.
 *
 * @param request - The incoming NextRequest
 * @param nextParam - The "next" query parameter value
 * @returns A safe absolute redirect URL
 */
export function resolveServerRedirectUrl(
  request: NextRequest,
  nextParam: string | null | undefined
): string {
  const origin = getOriginFromRequest(request);
  const path = safeNextPath(nextParam);
  return `${origin}${path}`;
}

/** The fallback redirect path for invalid inputs. */
export const AUTH_SERVER_FALLBACK_PATH = FALLBACK_PATH;
