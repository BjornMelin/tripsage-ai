/**
 * @fileoverview Helpers for generating BYOK telemetry span attributes.
 */

import type { TelemetrySpanAttributes } from "@/lib/telemetry/span";
import type { RateLimitResult } from "./_rate-limiter";

type Operation = "insert" | "delete";
type IdentifierType = "user" | "ip";

export type BuildKeySpanAttributesInput = {
  identifierType: IdentifierType;
  operation: Operation;
  rateLimit?: RateLimitResult;
  service: string;
  userId?: string;
};

/**
 * Produce normalized span attributes shared by BYOK RPC spans.
 *
 * @param input Context for the RPC call.
 * @returns Attribute map safe for telemetry export.
 */
export function buildKeySpanAttributes(
  input: BuildKeySpanAttributesInput
): TelemetrySpanAttributes {
  return {
    "keys.identifier_type": input.identifierType,
    "keys.operation": input.operation,
    "keys.service": input.service,
    "keys.user_id": input.userId ?? "anonymous",
    "ratelimit.has_limit": Boolean(input.rateLimit),
    "ratelimit.limit": input.rateLimit?.limit ?? 0,
    "ratelimit.remaining": input.rateLimit?.remaining ?? 0,
    "ratelimit.reset": input.rateLimit?.reset ?? 0,
    "ratelimit.success": input.rateLimit?.success ?? true,
  };
}
