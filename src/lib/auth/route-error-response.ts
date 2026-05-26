/**
 * @fileoverview Auth route error response helpers.
 */

import type { NextResponse } from "next/server";
import { errorResponse } from "@/lib/api/route-helpers";

interface AuthRouteErrorResponseOptions {
  code?: string;
  error?: string;
  extras?: Record<string, unknown>;
  reason: string;
  status: number;
}

/**
 * Builds a standardized auth route error response while preserving legacy fields.
 *
 * @param options - Response code, reason, status, and optional compatibility fields.
 * @returns Standardized Next.js JSON error response.
 */
export function authRouteErrorResponse({
  code,
  error,
  extras,
  reason,
  status,
}: AuthRouteErrorResponseOptions): NextResponse {
  const reservedKeys = new Set(["code", "error", "message", "reason"]);
  const responseExtras: Record<string, unknown> = {};

  if (extras) {
    for (const [key, value] of Object.entries(extras)) {
      if (!reservedKeys.has(key)) {
        responseExtras[key] = value;
      }
    }
  }

  responseExtras.message = reason;

  if (code) {
    responseExtras.code = code;
  }

  return errorResponse({
    error: error ?? code?.toLowerCase() ?? "auth_error",
    extras: responseExtras,
    reason,
    status,
  });
}
