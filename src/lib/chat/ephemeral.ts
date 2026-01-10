/**
 * @fileoverview Dev-only helpers for ephemeral chat behavior in E2E.
 */

import "server-only";

/**
 * Enables ephemeral chat persistence when running E2E/local dev without a DB.
 */
export function isChatEphemeralEnabled(): boolean {
  if (process.env.NODE_ENV === "production") return false;
  return (
    process.env.E2E_BYPASS_RATE_LIMIT === "1" ||
    process.env.E2E_BYPASS_RATE_LIMIT === "true"
  );
}
