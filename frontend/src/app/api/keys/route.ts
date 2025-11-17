/**
 * @fileoverview BYOK upsert route. Stores user-provided API keys in Supabase Vault via RPC.
 * Route: POST /api/keys
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { z } from "zod";
import type { RateLimitResult } from "@/app/api/keys/_rate-limiter";
import {
  buildRateLimiter,
  RateLimiterConfigurationError,
} from "@/app/api/keys/_rate-limiter";
import { buildKeySpanAttributes } from "@/app/api/keys/_telemetry";
import {
  API_CONSTANTS,
  checkAuthentication,
  getTrustedRateLimitIdentifier,
  redactErrorForLogging,
} from "@/lib/next/route-helpers";
import { insertUserApiKey, upsertUserGatewayBaseUrl } from "@/lib/supabase/rpc";
import { createServerSupabase } from "@/lib/supabase/server";
import { recordTelemetryEvent, withTelemetrySpan } from "@/lib/telemetry/span";
import { getKeys, type PostKeyBody, PostKeyBodySchema, postKey } from "./_handlers";

/**
 * BYOK routes return tenant-specific secrets and must stay fully dynamic. Next.js docs:
 * https://nextjs.org/docs/app/api-reference/file-conventions/route-segment-config#dynamic
 */
export const dynamic = "force-dynamic";
export const revalidate = 0;

type IdentifierType = "user" | "ip";

/**
 * Handle POST /api/keys to insert or replace a user's provider API key.
 *
 * @param req Next.js request containing JSON body with { service, apiKey }.
 * @returns 204 No Content on success; 400/401/429/500 on error.
 */
export async function POST(req: NextRequest) {
  try {
    const supabase = await createServerSupabase();
    const { user, isAuthenticated } = await checkAuthentication(supabase);
    const userObj = user as { id: string } | null;
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
    const identifierType: IdentifierType = userObj?.id ? "user" : "ip";
    let rateLimitMeta: RateLimitResult | undefined;
    if (ratelimitInstance) {
      const identifier = userObj?.id ?? getTrustedRateLimitIdentifier(req);
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

    // Check Content-Length before parsing to prevent memory exhaustion
    const contentLength = req.headers.get("content-length");
    if (contentLength) {
      const size = Number.parseInt(contentLength, 10);
      if (Number.isNaN(size) || size > API_CONSTANTS.maxBodySizeBytes) {
        recordTelemetryEvent("api.keys.size_limit", {
          attributes: { limit_bytes: API_CONSTANTS.maxBodySizeBytes, size_bytes: size },
          level: "warning",
        });
        return NextResponse.json(
          {
            code: "BAD_REQUEST",
            error: `Request body too large (max ${API_CONSTANTS.maxBodySizeBytes} bytes)`,
          },
          { status: 400 }
        );
      }
    }

    let validated: PostKeyBody;
    try {
      const body = await req.json();
      validated = PostKeyBodySchema.parse(body);
    } catch (parseError) {
      if (parseError instanceof z.ZodError) {
        const firstError = parseError.issues[0];
        recordTelemetryEvent("api.keys.validation_error", {
          attributes: {
            field: firstError?.path.join("."),
            message: firstError?.message,
          },
          level: "warning",
        });
        return NextResponse.json(
          {
            code: "BAD_REQUEST",
            error: firstError?.message ?? "Invalid request body",
          },
          { status: 400 }
        );
      }
      const { message: safeMessage, context: safeContext } = redactErrorForLogging(
        parseError,
        { operation: "json_parse" }
      );
      recordTelemetryEvent("api.keys.parse_error", {
        attributes: {
          message: safeMessage,
          ...safeContext,
        },
        level: "error",
      });
      return NextResponse.json(
        { code: "BAD_REQUEST", error: "Malformed JSON in request body" },
        { status: 400 }
      );
    }

    if (!isAuthenticated) {
      const { message: safeMessage, context: safeContext } = redactErrorForLogging(
        new Error("User not authenticated"),
        { operation: "auth_check" }
      );
      recordTelemetryEvent("api.keys.auth_error", {
        attributes: {
          message: safeMessage,
          ...safeContext,
        },
        level: "error",
      });
      return NextResponse.json(
        { code: "UNAUTHORIZED", error: "Authentication failed" },
        { status: 401 }
      );
    }

    const instrumentedInsert = (u: string, s: string, k: string) =>
      withTelemetrySpan(
        "keys.rpc.insert",
        {
          attributes: buildKeySpanAttributes({
            identifierType,
            operation: "insert",
            rateLimit: rateLimitMeta,
            service: s,
            userId: u,
          }),
        },
        async (span) => {
          try {
            await insertUserApiKey(u, s, k);
            span.setAttribute("keys.rpc.error", false);
          } catch (rpcError) {
            span.setAttribute("keys.rpc.error", true);
            throw rpcError;
          }
        }
      );

    // postKey normalizes and validates service identifiers before hitting Supabase RPCs.
    const result = await postKey(
      {
        insertUserApiKey: instrumentedInsert,
        supabase,
        // Store per-user Gateway base URL when provided.
        upsertUserGatewayBaseUrl: async (u: string, baseUrl: string) =>
          withTelemetrySpan(
            "keys.rpc.gateway_cfg.upsert",
            {
              attributes: buildKeySpanAttributes({
                identifierType,
                operation: "insert",
                rateLimit: rateLimitMeta,
                service: "gateway",
                userId: u,
              }),
            },
            async (span) => {
              try {
                await upsertUserGatewayBaseUrl(u, baseUrl);
                span.setAttribute("keys.rpc.error", false);
              } catch (rpcError) {
                span.setAttribute("keys.rpc.error", true);
                throw rpcError;
              }
            }
          ),
      },
      validated
    );
    return result;
  } catch (err) {
    // Redact potential secrets from logs
    const { message: safeMessage, context: safeContext } = redactErrorForLogging(err, {
      operation: "post_key",
    });
    recordTelemetryEvent("api.keys.post_error", {
      attributes: {
        message: safeMessage,
        ...safeContext,
      },
      level: "error",
    });
    return NextResponse.json(
      { code: "INTERNAL_ERROR", error: "Internal server error" },
      { status: 500 }
    );
  }
}

/**
 * Return metadata for the authenticated user's stored API keys.
 *
 * This endpoint returns only non-secret fields: service, created_at, last_used.
 *
 * @returns 200 with a list of key summaries; 401/500 on error.
 */
export async function GET() {
  try {
    const supabase = await createServerSupabase();
    return getKeys({ supabase });
  } catch (err) {
    const { message: safeMessage, context: safeContext } = redactErrorForLogging(err, {
      operation: "get_keys",
    });
    recordTelemetryEvent("api.keys.get_error", {
      attributes: {
        message: safeMessage,
        ...safeContext,
      },
      level: "error",
    });
    return NextResponse.json(
      { code: "INTERNAL_ERROR", error: "Internal server error" },
      { status: 500 }
    );
  }
}
