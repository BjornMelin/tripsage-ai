/**
 * @fileoverview Shared helpers for normalizing image sources and building proxy URLs.
 */

const IMAGE_PROXY_PATHNAME = "/api/images/proxy";

function tryParseUrl(value: string): URL | null {
  try {
    return new URL(value);
  } catch {
    return null;
  }
}

/**
 * Return true when value is an absolute http/https URL.
 */
export function isAbsoluteHttpUrl(value: string): boolean {
  const parsed = tryParseUrl(value);
  if (!parsed) return false;
  return parsed.protocol === "http:" || parsed.protocol === "https:";
}

/**
 * Normalize a potential image src into a value compatible with next/image:
 * - `/path` is allowed
 * - `https://...` is allowed
 *
 * Returns null when the input is not a valid path or URL string.
 */
export function normalizeNextImageSrc(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (!trimmed) return null;

  if (trimmed.startsWith("/")) return trimmed;
  if (isAbsoluteHttpUrl(trimmed)) return trimmed;

  return null;
}

/**
 * Build a same-origin proxy URL for a remote image URL.
 *
 * The proxy endpoint enforces a strict allowlist and size limits server-side.
 */
export function buildImageProxyUrl(remoteUrl: string): string {
  const url = new URL(IMAGE_PROXY_PATHNAME, "http://local.invalid");
  url.searchParams.set("url", remoteUrl);
  return `${url.pathname}?${url.searchParams.toString()}`;
}
