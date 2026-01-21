/**
 * @fileoverview Test helpers for origin resolution and protection.
 */

/**
 * Resolves the configured application origin for tests.
 *
 * Priority:
 * 1. APP_BASE_URL
 * 2. NEXT_PUBLIC_SITE_URL
 * 3. NEXT_PUBLIC_BASE_URL
 * 4. NEXT_PUBLIC_APP_URL
 * 5. Provided fallback origin
 *
 * @param fallback - The fallback origin to use if no environment variables are set.
 * @returns The resolved origin string.
 */
export function resolveTestOrigin(fallback: string): string {
  const candidates = [
    process.env.APP_BASE_URL,
    process.env.NEXT_PUBLIC_SITE_URL,
    process.env.NEXT_PUBLIC_BASE_URL,
    process.env.NEXT_PUBLIC_APP_URL,
  ];

  for (const candidate of candidates) {
    if (!candidate) continue;
    try {
      return new URL(candidate).origin;
    } catch {
      // Ignore invalid URLs in test environments
    }
  }

  return fallback;
}

/**
 * Automatically applies the "origin" header to a set of headers if missing.
 * Only applies to "unsafe" methods (POST, PUT, PATCH, DELETE).
 *
 * @param headers - The Headers object to modify.
 * @param method - The HTTP method of the request.
 * @param requestUrl - The full request URL (used for fallback origin).
 */
export function applyOriginHeader(
  headers: Headers,
  method: string,
  requestUrl: string
): void {
  const upperMethod = method.toUpperCase();
  const unsafeMethods = ["POST", "PUT", "PATCH", "DELETE"];

  if (!headers.has("origin") && unsafeMethods.includes(upperMethod)) {
    const urlObj = new URL(requestUrl);
    headers.set("origin", resolveTestOrigin(urlObj.origin));
  }
}
