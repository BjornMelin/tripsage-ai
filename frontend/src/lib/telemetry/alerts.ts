/**
 * @fileoverview Emits structured operational alerts for log-based monitoring.
 */

import "server-only";
import { TELEMETRY_SERVICE_NAME } from "@/lib/telemetry/constants";
import { recordTelemetryEvent } from "@/lib/telemetry/span";

export type AlertSeverity = "info" | "warning" | "error";

export type OperationalAlertOptions = {
  attributes?: Record<string, string | number | boolean | null | undefined>;
  severity?: AlertSeverity;
};

const ALERT_PREFIX = "[operational-alert]";

/**
 * Emits a structured log entry that downstream drains can convert into alerts.
 *
 * The alert is emitted to BOTH:
 * 1. Console (for log drain consumption by external monitoring)
 * 2. OpenTelemetry (for distributed tracing correlation)
 *
 * @param event - Stable event name (e.g., redis.unavailable).
 * @param options - Optional severity + attribute metadata.
 */
export function emitOperationalAlert(
  event: string,
  options: OperationalAlertOptions = {}
): void {
  const { severity = "error", attributes } = options;
  const payloadAttributes = attributes
    ? Object.entries(attributes).reduce<
        Record<string, string | number | boolean | null>
      >((acc, [key, value]) => {
        if (value !== undefined) {
          acc[key] = value;
        }
        return acc;
      }, {})
    : undefined;

  const timestamp = new Date().toISOString();
  const payload = {
    attributes: payloadAttributes ?? {},
    event,
    severity,
    source: TELEMETRY_SERVICE_NAME,
    timestamp,
  };

  // 1. Record to OTel for distributed tracing
  recordTelemetryEvent(`alert.${event}`, {
    attributes: {
      ...payloadAttributes,
      "alert.severity": severity,
      "alert.source": TELEMETRY_SERVICE_NAME,
      "alert.timestamp": timestamp,
    },
    level: severity,
  });

  // 2. Emit to console for log drain consumption (allowed per AGENTS.md)
  const sink = severity === "error" ? console.error : console.warn;
  sink.call(console, ALERT_PREFIX, JSON.stringify(payload));
}
