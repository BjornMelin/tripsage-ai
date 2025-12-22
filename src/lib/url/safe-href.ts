/**
 * @fileoverview Safe href sanitizer for AI/tool-derived links.
 */

const ALLOWED_PROTOCOLS = new Set(["http:", "https:", "mailto:"]);

/**
 * Returns a safe href string or undefined if unsafe/invalid.
 *
 * - Allows absolute http/https/mailto URLs.
 * - Allows same-origin relative paths that start with `/`.
 * - Blocks protocol-relative (`//`) and any other schemes (e.g., javascript:, data:).
 */
export function safeHref(raw?: string | null): string | undefined {
  if (!raw) return undefined;
  const trimmed = raw.trim();
  if (!trimmed) return undefined;

  if (trimmed.startsWith("//")) return undefined;
  if (trimmed.startsWith("/") || trimmed.startsWith("#") || trimmed.startsWith("?"))
    return trimmed;

  try {
    const url = new URL(trimmed);
    if (ALLOWED_PROTOCOLS.has(url.protocol)) return trimmed;
  } catch {
    // invalid URL
  }
  return undefined;
}
