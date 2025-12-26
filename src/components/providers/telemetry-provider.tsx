/**
 * @fileoverview React provider that initializes client-side OpenTelemetry tracing.
 */

"use client";

import { useEffect } from "react";

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
    // Lazy-load telemetry to keep OTEL libs out of the critical client bundle.
    import("@/lib/telemetry/client")
      .then(({ initTelemetry }) => {
        initTelemetry();
      })
      .catch((error: unknown) => {
        // Telemetry is optional on the client; swallow errors to avoid impacting UX.
        if (process.env.NODE_ENV === "development") {
          console.error("Telemetry initialization failed:", error);
        }
      });
  }, []);

  return null;
}
