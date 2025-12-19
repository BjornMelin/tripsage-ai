/**
 * @fileoverview Telemetry endpoint for AI demo events.
 */

import "server-only";

import type { TelemetryAiDemoRequest } from "@schemas/telemetry";
import { telemetryAiDemoRequestSchema } from "@schemas/telemetry";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import type { RouteContext, RouteParamsContext } from "@/lib/api/factory";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse } from "@/lib/api/route-helpers";
import { getServerEnvVarWithFallback } from "@/lib/env/server";
import { isValidInternalKey } from "@/lib/security/internal-key";
import { emitOperationalAlert } from "@/lib/telemetry/alerts";
import { hashTelemetryFingerprint } from "@/lib/telemetry/identifiers";

const MAX_BODY_BYTES = 16 * 1024;

/**
 * POST /api/telemetry/ai-demo
 *
 * Emit telemetry alert for AI demo events.
 *
 * @param req - Next.js request object
 * @param routeContext - Route context from withApiGuards
 * @returns JSON response with success status
 */
const guardedPOST = withApiGuards({
  auth: false,
  degradedMode: "fail_closed",
  maxBodyBytes: MAX_BODY_BYTES,
  rateLimit: "telemetry:ai-demo",
  schema: telemetryAiDemoRequestSchema,
  telemetry: "telemetry.ai-demo",
})((_req: NextRequest, _ctx: RouteContext, body: TelemetryAiDemoRequest) => {
  const hasDetail = Boolean(body.detail?.length);
  const detailLength = body.detail?.length ?? 0;
  const fullHash = body.detail ? hashTelemetryFingerprint(body.detail) : null;
  const detailHash = fullHash ? fullHash.slice(0, 16) : null;

  emitOperationalAlert("ai_demo.stream", {
    attributes: {
      detail_hash: detailHash,
      detail_length: detailLength,
      has_detail: hasDetail,
      status: body.status,
    },
    severity: body.status === "error" ? "warning" : "info",
  });
  return NextResponse.json({ ok: true });
});

export const POST = async (req: NextRequest, routeContext: RouteParamsContext) => {
  const enabled = getServerEnvVarWithFallback("ENABLE_AI_DEMO", false);
  if (!enabled) {
    return errorResponse({ error: "not_found", reason: "Not found", status: 404 });
  }

  // Return consistent 404 to avoid leaking feature/config state
  const internalKey = getServerEnvVarWithFallback("TELEMETRY_AI_DEMO_KEY", "");
  if (!internalKey) {
    return errorResponse({ error: "not_found", reason: "Not found", status: 404 });
  }

  const provided = req.headers.get("x-internal-key");
  if (!isValidInternalKey(provided, internalKey)) {
    return errorResponse({
      error: "unauthorized",
      reason: "Authentication required",
      status: 401,
    });
  }

  return await guardedPOST(req, routeContext);
};
