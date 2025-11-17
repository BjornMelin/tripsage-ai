/**
 * @fileoverview Client-safe tracer utilities for frontend telemetry.
 *
 * This module provides a client-safe implementation of telemetry tracing
 * that can be used in client components. It exports the same interface as
 * the server tracer for compatibility.
 */

import { type Tracer, trace } from "@opentelemetry/api";
import { TELEMETRY_SERVICE_NAME } from "./constants";

/**
 * Returns a client-safe tracer instance for frontend telemetry.
 *
 * In browser environments, this uses the OpenTelemetry API which may
 * be configured with browser-specific instrumentation. If no tracer
 * provider is registered, this returns a no-op tracer.
 *
 * @return OpenTelemetry tracer bound to the canonical frontend service name.
 */
export function getTelemetryTracer(): Tracer {
  return trace.getTracer(TELEMETRY_SERVICE_NAME);
}
