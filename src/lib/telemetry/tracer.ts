/**
 * @fileoverview Shared tracer utilities for frontend telemetry.
 */

import "server-only";

import { type Tracer, trace } from "@opentelemetry/api";
import { TELEMETRY_SERVICE_NAME } from "./constants";

/**
 * Returns the shared tracer instance for frontend telemetry.
 *
 * @return OpenTelemetry tracer bound to the canonical frontend service name.
 */
export function getTelemetryTracer(): Tracer {
  return trace.getTracer(TELEMETRY_SERVICE_NAME);
}
