/**
 * @fileoverview Safe href sanitizer for AI/tool-derived links.
 *
 * React does not sanitize URL protocols in href/src attributes. This helper
 * enforces a small allow-list for untrusted links before rendering.
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
  if (trimmed.startsWith("/")) return trimmed;

  try {
    const url = new URL(trimmed);
    if (ALLOWED_PROTOCOLS.has(url.protocol)) return trimmed;
  } catch {
    // invalid URL
  }
  return undefined;
}
