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
export function getRuntimeEnv(): "production" | "preview" | "development" | "test" {
  const vercelEnv = process.env.VERCEL_ENV;
  if (
    vercelEnv === "production" ||
    vercelEnv === "preview" ||
    vercelEnv === "development"
  ) {
    return vercelEnv;
  }

  if (process.env.NODE_ENV === "production") return "production";
  if (process.env.NODE_ENV === "test") return "test";
  return "development";
}
