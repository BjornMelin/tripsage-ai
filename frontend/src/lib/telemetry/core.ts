/**
 * @fileoverview Shared telemetry type definitions.
 *
 * Environment-agnostic type aliases used by both server and client telemetry modules.
 * This module contains no runtime dependencies on OpenTelemetry or environment-specific APIs.
 */

/**
 * Telemetry span attributes are key-value pairs attached to spans.
 */
export type TelemetrySpanAttributes = Record<string, string | number | boolean>;

/**
 * Options for wrapping operations in telemetry spans.
 */
export type WithTelemetrySpanOptions = {
  attributes?: TelemetrySpanAttributes;
  redactKeys?: string[];
};

/**
 * Options for recording telemetry events.
 */
export type TelemetryLogOptions = {
  attributes?: TelemetrySpanAttributes;
  level?: "info" | "warning" | "error";
};
