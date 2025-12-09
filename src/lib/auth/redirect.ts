/**
 * @fileoverview Safe redirect URL resolver for auth flows.
 */

import { getClientOrigin } from "@/lib/url/client-origin";

const FALLBACK_REDIRECT = "/dashboard";

/** Gets the base origin. */
function getBaseOrigin(): string {
  return getClientOrigin();
}

/**
 * Resolves the redirect URL.
 *
 * @param redirectTo - The redirect URL.
 * @param options - Resolution options.
 * @returns The resolved redirect URL.
 */
export function resolveRedirectUrl(
  redirectTo?: string,
  options?: { absolute?: boolean }
): string {
  const shouldReturnAbsolute = options?.absolute ?? false;
  if (!redirectTo) return FALLBACK_REDIRECT;
  try {
    const trimmed = redirectTo.trim();
    if (!trimmed) return FALLBACK_REDIRECT;

    // Block protocol-relative URLs
    if (trimmed.startsWith("//")) return FALLBACK_REDIRECT;

    // Preserve relative paths while normalizing
    if (trimmed.startsWith("/")) {
      const baseOrigin = getBaseOrigin();
      const target = new URL(trimmed, baseOrigin);
      if (target.origin !== baseOrigin) return FALLBACK_REDIRECT;
      const normalizedPath = target.pathname.replace(/\\/g, "/");
      if (normalizedPath.startsWith("//")) return FALLBACK_REDIRECT;
      const path = `${normalizedPath}${target.search}${target.hash}`;
      if (!path) return FALLBACK_REDIRECT;
      return shouldReturnAbsolute ? `${target.origin}${path}` : path;
    }

    const baseOrigin = getBaseOrigin();
    const target = new URL(trimmed, baseOrigin);
    if (!["http:", "https:"].includes(target.protocol)) {
      return FALLBACK_REDIRECT;
    }

    const allowedHosts = new Set<string>([new URL(baseOrigin).host]);
    [process.env.NEXT_PUBLIC_SITE_URL, process.env.APP_BASE_URL]
      .filter(Boolean)
      .forEach((value) => {
        try {
          allowedHosts.add(new URL(value as string).host);
        } catch {
          // ignore malformed env URLs
        }
      });

    const isAllowedHost = allowedHosts.has(target.host);
    const isSameOrigin = target.origin === baseOrigin;
    if (!isAllowedHost && !isSameOrigin) {
      return FALLBACK_REDIRECT;
    }

    const normalizedPath = target.pathname.replace(/\\/g, "/");
    if (normalizedPath.startsWith("//")) return FALLBACK_REDIRECT;

    const path = `${normalizedPath}${target.search}${target.hash}`;
    if (!path) return FALLBACK_REDIRECT;

    return shouldReturnAbsolute ? `${target.origin}${path}` : path;
  } catch {
    return FALLBACK_REDIRECT;
  }
}

/** The fallback redirect URL. */
export const AUTH_FALLBACK_REDIRECT = FALLBACK_REDIRECT;
