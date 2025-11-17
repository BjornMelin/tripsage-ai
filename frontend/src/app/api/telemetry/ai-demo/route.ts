/**
 * @fileoverview Telemetry endpoint for AI demo events.
 */

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { parseJsonBody } from "@/lib/next/route-helpers";
import { emitOperationalAlert } from "@/lib/telemetry/alerts";

type TelemetryPayload = {
  detail?: string;
  status: "success" | "error";
};

/**
 * POST /api/telemetry/ai-demo
 *
 * Emit telemetry alert for AI demo events.
 *
 * @param req - Next.js request object
 * @param routeContext - Route context from withApiGuards
 * @returns JSON response with success status
 */
export const POST = withApiGuards({
  auth: false,
  rateLimit: "telemetry:ai-demo",
  telemetry: "telemetry.ai-demo",
})(async (req: NextRequest) => {
  const parsed = await parseJsonBody(req);
  if ("error" in parsed) {
    return parsed.error;
  }
  const body = parsed.body as TelemetryPayload;
  if (body.status !== "success" && body.status !== "error") {
    return NextResponse.json({ ok: false }, { status: 400 });
  }

  emitOperationalAlert("ai_demo.stream", {
    attributes: {
      detail: body.detail ?? null,
      status: body.status,
    },
    severity: body.status === "error" ? "warning" : "info",
  });
  return NextResponse.json({ ok: true });
});
