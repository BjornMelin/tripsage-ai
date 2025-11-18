/**
 * @fileoverview BYOK upsert route. Stores user-provided API keys in Supabase Vault via RPC.
 * Route: POST /api/keys
 */

import "server-only";

// Security: Prevent caching of sensitive API key data per ADR-0024.
// With Cache Components enabled, route handlers are dynamic by default.
// Using withApiGuards({ auth: true }) ensures this route uses cookies/headers,
// making it dynamic and preventing caching. No 'use cache' directives are present.

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import type { RateLimitResult } from "@/app/api/keys/_rate-limiter";
import { buildKeySpanAttributes } from "@/app/api/keys/_telemetry";
import { withApiGuards } from "@/lib/api/factory";
import { API_CONSTANTS } from "@/lib/next/route-helpers";
import { type PostKeyBody, postKeyBodySchema } from "@/lib/schemas/api";
import { insertUserApiKey, upsertUserGatewayBaseUrl } from "@/lib/supabase/rpc";
import { recordTelemetryEvent, withTelemetrySpan } from "@/lib/telemetry/span";
import { getKeys, postKey } from "./_handlers";

type IdentifierType = "user" | "ip";

/**
 * Handle POST /api/keys to insert or replace a user's provider API key.
 *
 * @param req Next.js request containing JSON body with { service, apiKey }.
 * @param routeContext Route context from withApiGuards
 * @returns 204 No Content on success; 400/401/429/500 on error.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "keys:create",
  schema: postKeyBodySchema,
  // Custom telemetry handled below, factory telemetry disabled
})(async (req: NextRequest, { user, supabase }, validated: PostKeyBody) => {
  const userObj = user as { id: string } | null;
  const identifierType: IdentifierType = userObj?.id ? "user" : "ip";
  // Rate limit metadata not available from factory, using undefined for custom telemetry
  const rateLimitMeta: RateLimitResult | undefined = undefined;

  // Check Content-Length before parsing to prevent memory exhaustion
  // Note: This check happens after withApiGuards has already parsed the body,
  // but we keep it for defense-in-depth and telemetry.
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
});

/**
 * Return metadata for the authenticated user's stored API keys.
 *
 * This endpoint returns only non-secret fields: service, created_at, last_used.
 *
 * @param req Next.js request object
 * @param routeContext Route context from withApiGuards
 * @returns 200 with a list of key summaries; 401/500 on error.
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "keys:create", // Reuse create limit for GET
  // Custom telemetry handled in handler
})((_req: NextRequest, { supabase }) => {
  return getKeys({ supabase });
});
