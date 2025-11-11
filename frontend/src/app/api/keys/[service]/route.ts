/**
 * @fileoverview BYOK delete route. Removes a user API key from Supabase Vault.
 * Route: DELETE /api/keys/[service]
 */

import "server-only";

/**
 * BYOK routes are per-request and must not reuse cached responses. Next.js docs:
 * https://nextjs.org/docs/app/api-reference/file-conventions/route-segment-config#dynamic
 */
export const dynamic = "force-dynamic";
export const revalidate = 0;

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import {
  buildRateLimiter,
  RateLimiterConfigurationError,
  type RateLimitResult,
} from "@/app/api/keys/_rate-limiter";
import { buildKeySpanAttributes } from "@/app/api/keys/_telemetry";
import {
  getTrustedRateLimitIdentifier,
  redactErrorForLogging,
} from "@/lib/next/route-helpers";
import { deleteUserApiKey } from "@/lib/supabase/rpc";
import { createServerSupabase } from "@/lib/supabase/server";
import { withTelemetrySpan } from "@/lib/telemetry/span";

const ALLOWED_SERVICES = new Set(["openai", "openrouter", "anthropic", "xai"]);

type IdentifierType = "user" | "ip";

/**
 * Handle DELETE /api/keys/[service] to remove a user's provider API key.
 *
 * @param req Next.js request.
 * @param ctx Route params including the service identifier.
 * @returns 204 No Content on success; 400/401/429/500 on error.
 */
export async function DELETE(
  req: NextRequest,
  context: { params: Promise<{ service: string }> }
) {
  let serviceForLog: string | undefined;
  try {
    const supabase = await createServerSupabase();
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    const identifierType: IdentifierType = user?.id ? "user" : "ip";
    let ratelimitInstance: ReturnType<typeof buildRateLimiter>;
    try {
      ratelimitInstance = buildRateLimiter();
    } catch (configError) {
      if (configError instanceof RateLimiterConfigurationError) {
        return NextResponse.json(
          {
            code: "CONFIGURATION_ERROR",
            error: "Rate limiter configuration error",
          },
          { status: 500 }
        );
      }
      throw configError;
    }
    let rateLimitMeta: RateLimitResult | undefined;
    if (ratelimitInstance) {
      const identifier = user?.id ?? getTrustedRateLimitIdentifier(req);
      rateLimitMeta = await ratelimitInstance.limit(identifier);
      if (!rateLimitMeta.success) {
        return NextResponse.json(
          { code: "RATE_LIMIT", error: "Rate limit exceeded" },
          {
            headers: {
              "X-RateLimit-Limit": String(rateLimitMeta.limit),
              "X-RateLimit-Remaining": String(rateLimitMeta.remaining),
              "X-RateLimit-Reset": String(rateLimitMeta.reset),
            },
            status: 429,
          }
        );
      }
    }

    const { service } = await context.params;
    serviceForLog = service;
    if (!service || typeof service !== "string") {
      return NextResponse.json(
        { code: "BAD_REQUEST", error: "Invalid service" },
        { status: 400 }
      );
    }
    const normalizedService = service.trim().toLowerCase();
    if (!ALLOWED_SERVICES.has(normalizedService)) {
      return NextResponse.json(
        { code: "BAD_REQUEST", error: "Unsupported service" },
        { status: 400 }
      );
    }

    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    await withTelemetrySpan(
      "keys.rpc.delete",
      {
        attributes: buildKeySpanAttributes({
          identifierType,
          operation: "delete",
          rateLimit: rateLimitMeta,
          service: normalizedService,
          userId: user.id,
        }),
      },
      async (span) => {
        try {
          await deleteUserApiKey(user.id, normalizedService);
          span.setAttribute("keys.rpc.error", false);
        } catch (rpcError) {
          span.setAttribute("keys.rpc.error", true);
          throw rpcError;
        }
      }
    );
    return new NextResponse(null, { status: 204 });
  } catch (err) {
    const { message: safeMessage, context: safeContext } = redactErrorForLogging(err, {
      operation: "delete_key",
      service: serviceForLog,
    });
    console.error("/api/keys/[service] DELETE error:", {
      message: safeMessage,
      ...safeContext,
    });
    return NextResponse.json(
      { code: "INTERNAL_ERROR", error: "Internal server error" },
      { status: 500 }
    );
  }
}
