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

/** Constants for telemetry validation. */
const MAX_ATTRIBUTE_ENTRIES = 25;
const EVENT_NAME_PATTERN = /^[a-z][a-z0-9._]{0,99}$/i;

/**
 * Validates the attributes object to ensure it only contains primitive values.
 *
 * @param attributes - The attributes object to validate.
 * @returns True if the attributes are valid, false otherwise.
 */
function validateAttributes(
  attributes?: Record<string, unknown>
): attributes is Record<string, string | number | boolean> {
  if (!attributes) return true;
  const entries = Object.entries(attributes);
  if (entries.length > MAX_ATTRIBUTE_ENTRIES) return false;
  return entries.every(([, value]) => {
    const valueType = typeof value;
    return valueType === "string" || valueType === "number" || valueType === "boolean";
  });
}

/**
 * Record booking-related telemetry events from client interactions.
 *
 * Accepts JSON payloads and forwards them to OTEL spans without persisting user data.
 */
export const POST = withApiGuards({
  auth: false,
  rateLimit: "telemetry:post",
  telemetry: "telemetry.activities",
})(async (req: NextRequest) => {
  const parsed = await parseJsonBody(req);
  if ("error" in parsed) {
    return parsed.error;
  }

  const payload = parsed.body as Partial<ActivityTelemetryPayload>;
  const { attributes, eventName, level } = payload;
  if (
    !eventName ||
    typeof eventName !== "string" ||
    !EVENT_NAME_PATTERN.test(eventName)
  ) {
    return NextResponse.json(
      { ok: false, reason: "eventName required and must match pattern" },
      { status: 400 }
    );
  }

  if (!validateAttributes(attributes)) {
    return NextResponse.json(
      { ok: false, reason: "attributes must be primitives and <=25 entries" },
      { status: 400 }
    );
  }

  recordTelemetryEvent(eventName, {
    attributes: attributes ?? undefined,
    level: level ?? "info",
  });

  return NextResponse.json({ ok: true });
});
