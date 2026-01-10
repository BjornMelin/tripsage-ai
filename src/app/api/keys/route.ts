/**
 * @fileoverview BYOK upsert route. Stores user-provided API keys in Supabase Vault via RPC. Route: POST /api/keys
 */

import "server-only";

import { type PostKeyBody, postKeyBodySchema } from "@schemas/api";
import type { NextRequest } from "next/server";
import { buildKeySpanAttributes } from "@/app/api/keys/_telemetry";
import { withApiGuards } from "@/lib/api/factory";
import { requireUserId } from "@/lib/api/route-helpers";
import { insertUserApiKey, upsertUserGatewayBaseUrl } from "@/lib/supabase/rpc";
import { withTelemetrySpan } from "@/lib/telemetry/span";
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
  botId: true,
  rateLimit: "keys:create",
  schema: postKeyBodySchema,
  // Custom telemetry handled below, factory telemetry disabled
})(async (_req: NextRequest, { user, supabase }, validated: PostKeyBody) => {
  const userResult = requireUserId(user);
  if (!userResult.ok) return userResult.error;
  const userId = userResult.data;
  const identifierType: IdentifierType = "user";

  const instrumentedInsert = (u: string, s: string, k: string) =>
    withTelemetrySpan(
      "keys.rpc.insert",
      {
        attributes: buildKeySpanAttributes({
          identifierType,
          operation: "insert",
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
      userId,
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
  botId: true,
  rateLimit: "keys:create", // Reuse create limit for GET
  // Custom telemetry handled in handler
})((_req: NextRequest, { supabase, user }) => {
  const result = requireUserId(user);
  if (!result.ok) return result.error;
  const userId = result.data;
  return getKeys({ supabase, userId });
});
