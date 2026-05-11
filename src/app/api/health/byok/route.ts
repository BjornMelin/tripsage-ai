/**
 * @fileoverview Operator-only BYOK readiness endpoint.
 */

import "server-only";

import type { NextRequest, NextResponse } from "next/server";
import { NextResponse as JsonResponse } from "next/server";
import { PLANNED_ERROR_CODES } from "@/app/api/keys/_error-mapping";
import {
  errorResponse,
  forbiddenResponse,
  unauthorizedResponse,
} from "@/lib/api/route-helpers";
import { getServerEnvVarWithFallback } from "@/lib/env/server";
import { isValidInternalKey } from "@/lib/security/internal-key";
import { nowIso } from "@/lib/security/random";
import { checkByokVaultHealth } from "@/lib/supabase/rpc";
import {
  recordErrorOnSpan,
  recordTelemetryEvent,
  withTelemetrySpan,
} from "@/lib/telemetry/span";

const NO_STORE_HEADERS = { "Cache-Control": "no-store" } as const;
const OPERATOR_KEY_HEADER = "x-internal-key";

function noStore(response: NextResponse): NextResponse {
  response.headers.set("Cache-Control", "no-store");
  return response;
}

function getBearerToken(authHeader: string | null): string | null {
  if (!authHeader) return null;
  const [scheme, ...parts] = authHeader.trim().split(/\s+/);
  if (scheme?.toLowerCase() !== "bearer") return null;
  const token = parts.join(" ").trim();
  return token || null;
}

function getProvidedOperatorKey(req: NextRequest): string | null {
  return (
    req.headers.get(OPERATOR_KEY_HEADER) ??
    getBearerToken(req.headers.get("authorization"))
  );
}

function sanitizedHealthCheckError(): Error {
  return new Error("BYOK Vault health check failed");
}

export async function GET(req: NextRequest): Promise<NextResponse> {
  const expectedKey = getServerEnvVarWithFallback("BYOK_HEALTHCHECK_KEY", "");
  if (!expectedKey) {
    return errorResponse({
      error: "byok_health_not_configured",
      headers: NO_STORE_HEADERS,
      reason: "BYOK health check is not configured",
      status: 503,
    });
  }

  const providedKey = getProvidedOperatorKey(req);
  if (!providedKey) {
    return noStore(unauthorizedResponse());
  }

  if (!isValidInternalKey(providedKey, expectedKey)) {
    return noStore(forbiddenResponse("Invalid BYOK health check key"));
  }

  return await withTelemetrySpan(
    "health.byok",
    {
      attributes: {
        "health.check": "byok",
        "health.component": "vault",
      },
    },
    async (span) => {
      const startedAt = Date.now();
      try {
        await checkByokVaultHealth();
        const latencyMs = Date.now() - startedAt;
        span.setAttribute("health.latency_ms", latencyMs);
        span.setAttribute("health.status", "ok");

        return JsonResponse.json(
          {
            checks: {
              rpc: "ok",
              vault: "ok",
            },
            service: "tripsage-ai",
            status: "ok",
            timestamp: nowIso(),
          },
          { headers: NO_STORE_HEADERS, status: 200 }
        );
      } catch {
        const latencyMs = Date.now() - startedAt;
        span.setAttribute("health.latency_ms", latencyMs);
        span.setAttribute("health.status", "error");
        recordErrorOnSpan(span, sanitizedHealthCheckError());
        recordTelemetryEvent("health.byok_failure", {
          attributes: {
            code: PLANNED_ERROR_CODES.vaultUnavailable,
            latency_ms: latencyMs,
          },
          level: "error",
        });

        return errorResponse({
          error: PLANNED_ERROR_CODES.vaultUnavailable,
          headers: NO_STORE_HEADERS,
          reason: "BYOK Vault health check failed",
          status: 503,
        });
      }
    }
  );
}
