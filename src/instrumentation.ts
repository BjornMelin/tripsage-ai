/**
 * @fileoverview Next.js instrumentation hook for OpenTelemetry server-side tracing.
 *
 * This file is automatically executed by Next.js before the application starts.
 * It initializes @vercel/otel to enable automatic instrumentation of Route Handlers,
 * Server Components, and Middleware.
 */

import { registerOTel } from "@vercel/otel";
import { TELEMETRY_SERVICE_NAME } from "@/lib/telemetry/constants";

/**
 * Registers OpenTelemetry instrumentation for the Next.js application.
 *
 * This function is called by Next.js during application startup to enable
 * server-side tracing. The @vercel/otel wrapper handles all the complexity
 * of setting up NodeSDK, resource detection, and Next.js-specific instrumentation.
 */
export function register() {
  registerOTel({
    serviceName: TELEMETRY_SERVICE_NAME,
  });
}
