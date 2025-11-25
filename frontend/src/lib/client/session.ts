/**
 * @fileoverview Client-side session utilities.
 * Uses browser storage APIs - must only be imported in client components.
 */

"use client";

import { secureUuid } from "@/lib/security/random";

/**
 * Get or create a per-session identifier for error tracking and telemetry.
 *
 * The ID is stored in `sessionStorage` under the key `session_id`. If it does
 * not exist, a new ID is generated using `secureUuid()` and persisted. When
 * called in environments without access to `sessionStorage` (e.g., server
 * rendering, certain privacy contexts), the function returns `undefined`.
 *
 * @returns A stable session identifier string or `undefined` when unavailable.
 */
export function getSessionId(): string | undefined {
  try {
    let sessionId = sessionStorage.getItem("session_id");
    if (!sessionId) {
      sessionId = `session_${secureUuid()}`;
      sessionStorage.setItem("session_id", sessionId);
    }
    return sessionId;
  } catch {
    return undefined;
  }
}
