/**
 * @fileoverview Client-only Web Vitals reporter backed by the Next.js web-vitals hook.
 */

"use client";

import { useReportWebVitals } from "next/web-vitals";
import { sanitizePathnameForTelemetry } from "@/lib/telemetry/route-key";
import {
  WEB_VITALS_ENDPOINT,
  type WebVitalsReportPayload,
} from "@/lib/telemetry/web-vitals";

type WebVitalsMetric = Parameters<Parameters<typeof useReportWebVitals>[0]>[0];

// biome-ignore lint/style/useNamingConvention: Web Vitals callback, not a React component.
function reportWebVitals(metric: WebVitalsMetric): void {
  const payload: WebVitalsReportPayload = {
    delta: metric.delta,
    name: metric.name,
    navigationType: metric.navigationType,
    rating: metric.rating,
    route: sanitizePathnameForTelemetry(window.location.pathname),
    value: metric.value,
  };
  const body = JSON.stringify(payload);

  if (typeof navigator.sendBeacon === "function") {
    const beaconBody = new Blob([body], { type: "application/json" });
    if (navigator.sendBeacon(WEB_VITALS_ENDPOINT, beaconBody)) return;
  }

  if (typeof fetch !== "function") return;

  fetch(WEB_VITALS_ENDPOINT, {
    body,
    headers: { "content-type": "application/json" },
    keepalive: true,
    method: "POST",
  }).catch(() => undefined);
}

/**
 * Installs real-user Web Vitals reporting without wrapping the app tree in a client boundary.
 *
 * @returns Null; this component exists only for its reporting side effect.
 */
export function WebVitalsReporter() {
  useReportWebVitals(reportWebVitals);
  return null;
}
