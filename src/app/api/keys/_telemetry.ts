/**
 * @fileoverview Helpers for generating BYOK telemetry span attributes.
 */

import "server-only";

import { hashTelemetryIdentifier } from "@/lib/telemetry/identifiers";
import type { TelemetrySpanAttributes } from "@/lib/telemetry/span";

type Operation = "insert" | "delete";
type IdentifierType = "user" | "ip";

export type RateLimitMetadata = {
  limit: number;
  remaining: number;
  reset: number;
  success: boolean;
};

export type BuildKeySpanAttributesInput = {
  identifierType: IdentifierType;
  operation: Operation;
  rateLimit?: RateLimitMetadata;
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
  const attrs: TelemetrySpanAttributes = {
    "keys.identifier_type": input.identifierType,
    "keys.operation": input.operation,
    "keys.service": input.service,
    "ratelimit.has_limit": Boolean(input.rateLimit),
    "ratelimit.limit": input.rateLimit?.limit ?? 0,
    "ratelimit.remaining": input.rateLimit?.remaining ?? 0,
    "ratelimit.reset": input.rateLimit?.reset ?? 0,
    "ratelimit.success": input.rateLimit?.success ?? true,
  };

  const userIdHash = input.userId ? hashTelemetryIdentifier(input.userId) : null;
  if (userIdHash) {
    attrs["keys.user_id_hash"] = userIdHash;
  }

  return attrs;
}
