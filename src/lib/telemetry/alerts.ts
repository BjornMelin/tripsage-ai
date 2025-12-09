/**
 * @fileoverview Emits structured operational alerts for log-based monitoring.
 *
 * Alerts are recorded via OpenTelemetry for distributed tracing and integration
 * with external monitoring systems. Log drains can subscribe to OTEL events
 * to trigger alerting workflows.
 */

import "server-only";
import { TELEMETRY_SERVICE_NAME } from "@/lib/telemetry/constants";
import { recordTelemetryEvent } from "@/lib/telemetry/span";

export type AlertSeverity = "info" | "warning" | "error";

export type OperationalAlertOptions = {
  attributes?: Record<string, string | number | boolean | null | undefined>;
  severity?: AlertSeverity;
};

/**
 * Emits a structured operational alert via OpenTelemetry.
 *
 * Alerts are recorded as telemetry events that external monitoring systems
 * can consume to trigger alerting workflows. Downstream log drains and
 * OTEL collectors integrate with the telemetry infrastructure.
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

  // Record to OTel for distributed tracing and monitoring integration
  recordTelemetryEvent(`alert.${event}`, {
    attributes: {
      ...payloadAttributes,
      "alert.severity": severity,
      "alert.source": TELEMETRY_SERVICE_NAME,
      "alert.timestamp": timestamp,
    },
    level: severity,
  });
}
