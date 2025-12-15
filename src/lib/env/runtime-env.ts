/**
 * @fileoverview Runtime environment detection helpers.
 */

import "server-only";

/**
 * Determine the runtime environment for server-side feature gating.
 *
 * Prefers `VERCEL_ENV` when present and otherwise falls back to a normalized
 * value derived from `NODE_ENV`.
 */
export function getRuntimeEnv():
  | "production"
  | "preview"
  | "development"
  | "test"
  | string {
  return (
    process.env.VERCEL_ENV ??
    (process.env.NODE_ENV === "production"
      ? "production"
      : process.env.NODE_ENV === "test"
        ? "test"
        : "development")
  );
}
