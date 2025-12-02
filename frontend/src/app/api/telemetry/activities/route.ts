/**
 * @fileoverview Telemetry endpoint for activity booking events.
 *
 * Allows client-side booking interactions to be recorded via OTEL spans.
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { parseJsonBody } from "@/lib/api/route-helpers";
import { recordTelemetryEvent } from "@/lib/telemetry/span";

/** Shape of activity booking telemetry payloads accepted by this route. */
type ActivityTelemetryPayload = {
  attributes?: Record<string, string | number | boolean>;
  eventName: string;
  level?: "info" | "warning" | "error";
};

/**
 * Record booking-related telemetry events from client interactions.
 *
 * Accepts JSON payloads and forwards them to OTEL spans without persisting user data.
 */
export const POST = withApiGuards({
  auth: false,
  telemetry: "telemetry.activities",
})(async (req: NextRequest) => {
  const parsed = await parseJsonBody(req);
  if ("error" in parsed) {
    return parsed.error;
  }

  const payload = parsed.body as Partial<ActivityTelemetryPayload>;
  const { attributes, eventName, level } = payload;
  if (!eventName || typeof eventName !== "string") {
    return NextResponse.json(
      { ok: false, reason: "eventName required" },
      { status: 400 }
    );
  }

  recordTelemetryEvent(eventName, {
    attributes: attributes ?? undefined,
    level: level ?? "info",
  });

  return NextResponse.json({ ok: true });
});
