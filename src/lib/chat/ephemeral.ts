/**
 * @fileoverview Dev-only helpers for ephemeral chat behavior in E2E.
 */

import "server-only";

/**
 * Enables ephemeral chat persistence when running E2E without a DB.
 */
export function isChatEphemeralEnabled(): boolean {
  if (process.env.NODE_ENV === "production") return false;
  return process.env.E2E === "1" || process.env.E2E === "true";
}
