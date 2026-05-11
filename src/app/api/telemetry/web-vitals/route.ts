/**
 * @fileoverview Telemetry endpoint for browser Web Vitals reports.
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, parseJsonBody } from "@/lib/api/route-helpers";
import { recordTelemetryEvent } from "@/lib/telemetry/span";
import {
  isWebVitalsMetricInRange,
  normalizeWebVitalsRoute,
  roundWebVitalsMetricValue,
  WEB_VITAL_NAMES,
  WEB_VITAL_NAVIGATION_TYPES,
  WEB_VITAL_RATINGS,
  WEB_VITAL_ROUTE_PATTERN,
} from "@/lib/telemetry/web-vitals";

const webVitalsPayloadSchema = z.strictObject({
  delta: z.number().finite().nonnegative(),
  name: z.enum(WEB_VITAL_NAMES),
  navigationType: z.enum(WEB_VITAL_NAVIGATION_TYPES).optional(),
  rating: z.enum(WEB_VITAL_RATINGS).optional(),
  route: z.string().min(1).max(200).regex(WEB_VITAL_ROUTE_PATTERN),
  value: z.number().finite().nonnegative(),
});

/**
 * Record low-cardinality browser Web Vitals as telemetry events.
 *
 * @returns JSON response confirming acceptance or a standardized validation error.
 */
export const POST = withApiGuards({
  auth: false,
  degradedMode: "fail_closed",
  rateLimit: "telemetry:post",
  telemetry: "telemetry.web-vitals",
})(async (req: NextRequest) => {
  const parsed = await parseJsonBody(req);
  if (!parsed.ok) return parsed.error;

  const validation = webVitalsPayloadSchema.safeParse(parsed.data);
  if (!validation.success) {
    return errorResponse({
      error: "invalid_request",
      issues: validation.error.issues,
      reason: "Web Vitals payload validation failed",
      status: 400,
    });
  }

  const metric = validation.data;
  if (
    !isWebVitalsMetricInRange(metric.name, metric.delta) ||
    !isWebVitalsMetricInRange(metric.name, metric.value)
  ) {
    return errorResponse({
      error: "invalid_request",
      reason: "Web Vitals metric value out of accepted range",
      status: 400,
    });
  }

  const route = normalizeWebVitalsRoute(metric.route);
  recordTelemetryEvent("web_vitals.reported", {
    attributes: {
      clientMetricRating: metric.rating ?? "unknown",
      metricDelta: roundWebVitalsMetricValue(metric.name, metric.delta),
      metricName: metric.name,
      metricValue: roundWebVitalsMetricValue(metric.name, metric.value),
      navigationType: metric.navigationType ?? "unknown",
      route,
    },
    level: "info",
  });

  return NextResponse.json({ ok: true });
});
