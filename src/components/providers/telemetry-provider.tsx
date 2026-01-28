/**
 * @fileoverview React provider that initializes client-side OpenTelemetry tracing.
 */

"use client";

import { useEffect } from "react";

const ENABLE_CLIENT_TELEMETRY =
  process.env.NEXT_PUBLIC_OTEL_CLIENT_ENABLED === "true" &&
  Boolean(process.env.NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT);

/**
 * TelemetryProvider component.
 *
 * Initializes client-side OpenTelemetry tracing on mount. Uses useEffect to
 * ensure initialization only happens in the browser (not during SSR).
 *
 * This component renders nothing and is purely for side effects.
 *
 * @returns null (renders nothing)
 */
export function TelemetryProvider(): null {
  useEffect(() => {
    if (!ENABLE_CLIENT_TELEMETRY) {
      return;
    }

    // Lazy-load telemetry to keep OTEL libs out of the critical client bundle.
    import("@/lib/telemetry/client")
      .then(({ initTelemetry }) => {
        initTelemetry();
      })
      .catch(() => {
        // Telemetry is optional on the client; swallow errors to avoid impacting UX.
      });
  }, []);

  return null;
}
