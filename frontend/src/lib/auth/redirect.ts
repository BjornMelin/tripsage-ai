/**
 * @fileoverview Safe redirect URL resolver for auth flows.
 */

const FALLBACK_REDIRECT = "/dashboard";

/** Gets the base origin. */
function getBaseOrigin(): string {
  if (typeof window !== "undefined" && window.location?.origin) {
    return window.location.origin;
  }
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL;
  if (siteUrl) {
    return new URL(siteUrl).origin;
  }
  const appBaseUrl = process.env.APP_BASE_URL;
  if (appBaseUrl) {
    return new URL(appBaseUrl).origin;
  }
  return "http://localhost:3000";
}

/**
 * Resolves the redirect URL.
 *
 * @param redirectTo - The redirect URL.
 * @returns The resolved redirect URL.
 */
export function resolveRedirectUrl(redirectTo?: string): string {
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
      const path = `${target.pathname}${target.search}${target.hash}`;
      return path || FALLBACK_REDIRECT;
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
    return isAllowedHost || isSameOrigin ? target.toString() : FALLBACK_REDIRECT;
  } catch {
    return FALLBACK_REDIRECT;
  }
}

/** The fallback redirect URL. */
export const AUTH_FALLBACK_REDIRECT = FALLBACK_REDIRECT;
