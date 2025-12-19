/**
 * @fileoverview Low-cardinality route key helpers for telemetry and alerts.
 */

function isUuidLike(value: string): boolean {
  // Basic UUID v4-ish matcher (case-insensitive); sufficient for telemetry normalization.
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
}

function isNumericId(value: string): boolean {
  return /^[0-9]{1,18}$/.test(value);
}

/**
 * Sanitizes a URL pathname into a low-cardinality telemetry route key.
 *
 * Behavior:
 * - Empty/root pathnames normalize to `"/"`.
 * - Trailing slashes are removed via segment normalization (e.g. `"/foo/"` → `"/foo"`).
 * - UUID-like segments become `":uuid"` and numeric segments become `":id"`.
 *
 * Callers must pass a pathname only (no query string or hash); those are not parsed here.
 */
export function sanitizePathnameForTelemetry(pathname: string): string {
  const parts = pathname.split("/").filter(Boolean);
  const sanitized = parts.map((part) => {
    if (isNumericId(part)) return ":id";
    if (isUuidLike(part)) return ":uuid";
    return part;
  });
  return `/${sanitized.join("/")}`;
}
