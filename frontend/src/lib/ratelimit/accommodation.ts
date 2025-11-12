/**
 * @fileoverview Accommodation workflow rate-limit helpers.
 */

import type { GuardrailRateLimit } from "@/lib/agents/runtime";

/**
 * Build a GuardrailRateLimit for accommodation search.
 *
 * @param identifier Stable user or IP-based identifier (already hashed if needed).
 * @returns Rate-limit config: 10 requests per minute by default.
 */
export function buildAccommodationRateLimit(
  identifier: string
): GuardrailRateLimit {
  return {
    identifier,
    limit: 10,
    window: "1 m",
  };
}

