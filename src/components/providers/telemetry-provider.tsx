/**
 * @fileoverview React provider that initializes client-side OpenTelemetry tracing.
 */

"use client";

import { useEffect } from "react";
import { initTelemetry } from "@/lib/telemetry/client";

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
    // Initialize telemetry only in browser environment
    initTelemetry();
  }, []);

  return null;
}
