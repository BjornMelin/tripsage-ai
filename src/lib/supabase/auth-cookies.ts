/**
 * @fileoverview Supabase auth cookie detection helpers for SSR and legacy cookies.
 */

import "server-only";

export type SupabaseCookie = { name: string; value: string };

export function isSupabaseSsrAuthCookieName(cookieName: string): boolean {
  if (!cookieName.startsWith("sb-")) return false;
  if (cookieName.endsWith("-auth-token")) return true;
  return /-auth-token\.\d+$/.test(cookieName);
}

export function hasSupabaseAuthCookies(cookies: SupabaseCookie[]): boolean {
  return cookies.some((cookie) => {
    if (!cookie.value?.trim()) return false;
    const name = cookie.name;
    if (name === "sb-access-token" || name === "sb-refresh-token") return true;
    return isSupabaseSsrAuthCookieName(name);
  });
}

export function hasSupabaseAuthCookiesFromHeader(cookieHeader: string | null): boolean {
  if (!cookieHeader) return false;
  const entries = cookieHeader
    .split(";")
    .map((part) => part.trim())
    .filter((part) => part.length > 0);

  for (const entry of entries) {
    const [name, value] = entry.split("=");
    if (!name || !value?.trim()) continue;
    if (name === "sb-access-token" || name === "sb-refresh-token") return true;
    if (isSupabaseSsrAuthCookieName(name)) return true;
  }

  return false;
}
