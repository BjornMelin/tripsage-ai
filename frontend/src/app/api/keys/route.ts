/**
 * @fileoverview BYOK upsert route. Stores user-provided API keys in Supabase Vault via RPC.
 * Route: POST /api/keys
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import type { RateLimitResult } from "@/app/api/keys/_rate-limiter";
import { buildRateLimiter } from "@/app/api/keys/_rate-limiter";
import { buildKeySpanAttributes } from "@/app/api/keys/_telemetry";
import { getClientIpFromHeaders } from "@/lib/next/route-helpers";
import { insertUserApiKey } from "@/lib/supabase/rpc";
import { createServerSupabase } from "@/lib/supabase/server";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import { getKeys, postKey } from "./_handlers";

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
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    const ratelimitInstance = buildRateLimiter();
    const identifierType: IdentifierType = user?.id ? "user" : "ip";
    let rateLimitMeta: RateLimitResult | undefined;
    if (ratelimitInstance) {
      const identifier = user?.id ?? getClientIpFromHeaders(req.headers);
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

    let service: string | undefined;
    let apiKey: string | undefined;
    try {
      const body = await req.json();
      service = body.service;
      apiKey = body.apiKey;
    } catch (parseError) {
      const message =
        parseError instanceof Error ? parseError.message : "Unknown JSON parse error";
      console.error("/api/keys POST JSON parse error:", { message });
      return NextResponse.json(
        { code: "BAD_REQUEST", error: "Malformed JSON in request body" },
        { status: 400 }
      );
    }

    if (
      !service ||
      !apiKey ||
      typeof service !== "string" ||
      typeof apiKey !== "string"
    ) {
      return NextResponse.json(
        { code: "BAD_REQUEST", error: "Invalid request body" },
        { status: 400 }
      );
    }

    if (authError || !user) {
      console.error("/api/keys POST auth error:", {
        message: authError?.message ?? "User not found",
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
          attributes: {
            ...buildKeySpanAttributes({
              identifierType,
              operation: "insert",
              rateLimit: rateLimitMeta,
              service: s,
              userId: u,
            }),
            "keys.api_key": k,
          },
          redactKeys: ["keys.api_key"],
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

    // postKey lowercases and validates service identifiers before hitting Supabase RPCs.
    return postKey(
      { insertUserApiKey: instrumentedInsert, supabase },
      { apiKey, service }
    );
  } catch (err) {
    // Redact potential secrets from logs
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("/api/keys POST error:", { message });
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
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("/api/keys GET error:", { message });
    return NextResponse.json(
      { code: "INTERNAL_ERROR", error: "Internal server error" },
      { status: 500 }
    );
  }
}
