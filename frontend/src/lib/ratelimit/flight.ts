/**
 * @fileoverview Flight workflow rate-limit helpers.
 */

import type { GuardrailRateLimit } from "@/lib/agents/runtime";

/**
 * Build a GuardrailRateLimit for flight search.
 *
 * @param identifier Stable user or IP-based identifier (already hashed if needed).
 * @returns Rate-limit config: 8 requests per minute by default.
 */
export function buildFlightRateLimit(identifier: string): GuardrailRateLimit {
  return {
    identifier,
    limit: 8,
    window: "1 m",
  };
}
