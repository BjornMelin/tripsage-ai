/**
 * @fileoverview Shared tracer utilities for TripSage telemetry.
 */

import { type Tracer, trace } from "@opentelemetry/api";
import { TELEMETRY_SERVICE_NAME } from "./constants";

/**
 * Returns the shared tracer instance for TripSage telemetry.
 *
 * @returns OpenTelemetry tracer bound to the canonical shared service name.
 */
export function getTelemetryTracer(): Tracer {
  return trace.getTracer(TELEMETRY_SERVICE_NAME);
}
