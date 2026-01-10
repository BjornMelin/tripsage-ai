/**
 * @fileoverview BYOK delete route. Removes a user API key from Supabase Vault. Route: DELETE /api/keys/[service]
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { buildKeySpanAttributes } from "@/app/api/keys/_telemetry";
import type { RouteParamsContext } from "@/lib/api/factory";
import { withApiGuards } from "@/lib/api/factory";
import {
  errorResponse,
  parseStringId,
  redactErrorForLogging,
  requireUserId,
} from "@/lib/api/route-helpers";
import { deleteUserApiKey, deleteUserGatewayBaseUrl } from "@/lib/supabase/rpc";
import { recordTelemetryEvent, withTelemetrySpan } from "@/lib/telemetry/span";
import { vaultUnavailableResponse } from "../_error-mapping";

const ALLOWED_SERVICES = new Set([
  "openai",
  "openrouter",
  "anthropic",
  "xai",
  "gateway",
]);

type IdentifierType = "user" | "ip";

/**
 * Handle DELETE /api/keys/[service] to remove a user's provider API key.
 *
 * @param req Next.js request.
 * @param context Route params including the service identifier.
 * @param routeContext Route context from withApiGuards
 * @returns 204 No Content on success; 400/401/429/500 on error.
 */
export function DELETE(
  req: NextRequest,
  context: { params: Promise<{ service: string }> }
): Promise<Response> {
  return withApiGuards({
    auth: true,
    botId: true,
    rateLimit: "keys:delete",
    // Custom telemetry handled below
  })(async (_req: NextRequest, { user }, _data, routeContext: RouteParamsContext) => {
    let serviceForLog: string | undefined;
    try {
      const result = requireUserId(user);
      if (!result.ok) return result.error;
      const userId = result.data;
      const identifierType: IdentifierType = "user";

      const serviceResult = await parseStringId(routeContext, "service");
      if (!serviceResult.ok) return serviceResult.error;
      const service = serviceResult.data;
      serviceForLog = service;
      const normalizedService = service.trim().toLowerCase();
      if (!ALLOWED_SERVICES.has(normalizedService)) {
        return errorResponse({
          error: "bad_request",
          reason: "Unsupported service",
          status: 400,
        });
      }

      await withTelemetrySpan(
        "keys.rpc.delete",
        {
          attributes: buildKeySpanAttributes({
            identifierType,
            operation: "delete",
            service: normalizedService,
            userId,
          }),
        },
        async (span) => {
          try {
            if (normalizedService === "gateway") {
              await deleteUserGatewayBaseUrl(userId);
            }
            await deleteUserApiKey(userId, normalizedService);
            span.setAttribute("keys.rpc.error", false);
          } catch (rpcError) {
            span.setAttribute("keys.rpc.error", true);
            throw rpcError;
          }
        }
      );
      return new NextResponse(null, { status: 204 });
    } catch (err) {
      const { message: safeMessage, context: safeContext } = redactErrorForLogging(
        err,
        {
          operation: "delete_key",
          service: serviceForLog,
        }
      );
      recordTelemetryEvent("api.keys.delete_error", {
        attributes: {
          message: safeMessage,
          service: serviceForLog ?? "unknown",
          ...safeContext,
        },
        level: "error",
      });
      return vaultUnavailableResponse("Failed to delete API key", err);
    }
  })(req, context);
}
