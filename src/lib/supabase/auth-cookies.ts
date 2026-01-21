/**
 * @fileoverview Supabase auth cookie detection helpers for SSR and legacy cookies.
 */

import "server-only";

/**
 * Minimal cookie representation for auth detection.
 */
export type SupabaseCookie = { name: string; value: string };

/**
 * Checks if a cookie name matches the Supabase SSR auth token pattern.
 *
 * Matches both the base token and chunked tokens (sb-*-auth-token or sb-*-auth-token.N).
 *
 * @param cookieName - The name of the cookie to check.
 * @returns True if it matches the Supabase auth token pattern.
 */
export function isSupabaseSsrAuthCookieName(cookieName: string): boolean {
  if (!cookieName.startsWith("sb-")) return false;
  if (cookieName.endsWith("-auth-token")) return true;
  return /-auth-token\.\d+$/.test(cookieName);
}

/**
 * Determines whether any cookie in the array is a Supabase authentication cookie.
 *
 * @param cookies - Array of SupabaseCookie to inspect
 * @returns `true` if at least one auth cookie with a non-empty value is found, `false` otherwise.
 */
export function hasSupabaseAuthCookies(cookies: SupabaseCookie[]): boolean {
  return cookies.some((cookie) => {
    if (!cookie.value?.trim()) return false;
    const name = cookie.name;
    if (name === "sb-access-token" || name === "sb-refresh-token") return true;
    return isSupabaseSsrAuthCookieName(name);
  });
}

/**
 * Checks if a raw Cookie header contains any Supabase authentication cookies.
 *
 * Parses the header string and validates both legacy and modern cookie names.
 *
 * @param cookieHeader - The raw 'Cookie' header value.
 * @returns True if at least one valid auth cookie is found.
 */
export function hasSupabaseAuthCookiesFromHeader(cookieHeader: string | null): boolean {
  if (!cookieHeader) return false;
  const entries = cookieHeader
    .split(";")
    .map((part) => part.trim())
    .filter((part) => part.length > 0);

  for (const entry of entries) {
    const eqIndex = entry.indexOf("=");
    if (eqIndex === -1) continue;
    const name = entry.slice(0, eqIndex);
    const value = entry.slice(eqIndex + 1);

    if (!name || !value?.trim()) continue;
    if (name === "sb-access-token" || name === "sb-refresh-token") return true;
    if (isSupabaseSsrAuthCookieName(name)) return true;
  }

  return false;
}
