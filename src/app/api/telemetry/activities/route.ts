/**
 * @fileoverview Telemetry endpoint for activity booking events.
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, parseJsonBody } from "@/lib/api/route-helpers";
import { recordTelemetryEvent } from "@/lib/telemetry/span";

/** Constants for telemetry validation. */
const MAX_ATTRIBUTE_ENTRIES = 25;
const EVENT_NAME_PATTERN = /^[a-z][a-z0-9._]{0,99}$/i;

const telemetryAttributesSchema = z
  .record(z.string(), z.union([z.string(), z.number(), z.boolean()]))
  .refine((attributes) => Object.keys(attributes).length <= MAX_ATTRIBUTE_ENTRIES, {
    error: `attributes must be primitives and <=${MAX_ATTRIBUTE_ENTRIES} entries`,
  });

const activityTelemetryPayloadSchema = z.strictObject({
  attributes: telemetryAttributesSchema.optional(),
  eventName: z
    .string()
    .regex(EVENT_NAME_PATTERN, { error: "eventName required and must match pattern" }),
  level: z.enum(["info", "warning", "error"]).optional(),
});

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
  if (!parsed.ok) return parsed.error;

  const validation = activityTelemetryPayloadSchema.safeParse(parsed.data);
  if (!validation.success) {
    return errorResponse({
      error: "invalid_request",
      issues: validation.error.issues,
      reason: "Telemetry payload validation failed",
      status: 400,
    });
  }

  recordTelemetryEvent(validation.data.eventName, {
    attributes: validation.data.attributes,
    level: validation.data.level ?? "info",
  });

  return NextResponse.json({ ok: true });
});
