/**
 * @fileoverview Next.js instrumentation hook for OpenTelemetry server-side tracing.
 */

import { OpenTelemetry } from "@ai-sdk/otel";
import { registerOTel } from "@vercel/otel";
import { registerTelemetry } from "ai";
import { TELEMETRY_SERVICE_NAME } from "@/lib/telemetry/constants";

/**
 * Registers OpenTelemetry instrumentation for the Next.js application.
 *
 * This function is called by Next.js during application startup to enable
 * server-side tracing. The @vercel/otel wrapper handles all the complexity
 * of setting up NodeSDK, resource detection, and Next.js-specific instrumentation.
 */
export async function register() {
  registerOTel({
    serviceName: TELEMETRY_SERVICE_NAME,
  });
  registerTelemetry(new OpenTelemetry({ runtimeContext: true }));

  // Initialize security modules on server runtime only
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const { initMfa } = await import("@/lib/security/mfa");
    initMfa();
  }
}
