/**
 * @fileoverview Hardened sanitizer for the auth confirm `next` query parameter.
 *
 * Prevents open redirect by allowlisting internal, app-relative paths.
 */

import "server-only";

export const AUTH_CONFIRM_DEFAULT_NEXT = "/dashboard";

// Intentionally restrictive allowlist: auth confirm links are user-controlled inputs and a common
// open-redirect vector. Start with the primary post-auth landing area only; expand via explicit
// allowlisted prefixes (and tests) as new flows require it. Never allow external URLs or /auth/*.
export const AUTH_CONFIRM_ALLOWED_PREFIXES = ["/dashboard"] as const;

function decodeOnce(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

function isAllowedNextPath(pathname: string): boolean {
  return AUTH_CONFIRM_ALLOWED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)
  );
}

export function sanitizeAuthConfirmNextParam(rawNext: string | null): string {
  if (!rawNext) return AUTH_CONFIRM_DEFAULT_NEXT;

  const decoded = decodeOnce(rawNext.trim());

  // Only allow internal, app-relative paths.
  if (!decoded.startsWith("/")) return AUTH_CONFIRM_DEFAULT_NEXT;
  if (decoded.startsWith("//")) return AUTH_CONFIRM_DEFAULT_NEXT;
  if (decoded.includes("\\")) return AUTH_CONFIRM_DEFAULT_NEXT;
  if (/[\r\n\t]/.test(decoded)) return AUTH_CONFIRM_DEFAULT_NEXT;

  try {
    // URL parsing defends against tricky values like "/\\evil", etc.
    const parsed = new URL(decoded, "https://app.local");
    const nextPath = `${parsed.pathname}${parsed.search}${parsed.hash}`;
    return isAllowedNextPath(parsed.pathname) ? nextPath : AUTH_CONFIRM_DEFAULT_NEXT;
  } catch {
    return AUTH_CONFIRM_DEFAULT_NEXT;
  }
}
