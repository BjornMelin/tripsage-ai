/**
 * @fileoverview Server-side logging helpers backed by OpenTelemetry.
 *
 * Provides lightweight helpers to emit structured log events without using
 * console.* in production code. The logger is a thin shim over
 * recordTelemetryEvent so all emitted messages travel through the same
 * tracing/export pipeline as the rest of our telemetry surface. For client
 * components/tests, prefer direct console usage guarded by NODE_ENV checks.
 */

import "server-only";

import type { TelemetrySpanAttributes } from "@/lib/telemetry/span";
import { recordTelemetryEvent, sanitizeAttributes } from "@/lib/telemetry/span";

type LogLevel = "info" | "warning" | "error";

export type LogMetadata = Record<string, unknown>;

export interface CreateServerLoggerOptions {
  /**
   * Keys in metadata to redact from telemetry logs.
   * @default []
   */
  redactKeys?: string[];
}

export interface ServerLogger {
  error: (message: string, metadata?: LogMetadata) => void;
  info: (message: string, metadata?: LogMetadata) => void;
  warn: (message: string, metadata?: LogMetadata) => void;
}

function normalizeAttributes(
  scope: string,
  message: string,
  metadata?: LogMetadata
): TelemetrySpanAttributes {
  const attributes: TelemetrySpanAttributes = {
    "log.message": message,
    "log.scope": scope,
  };

  if (!metadata) {
    return attributes;
  }

  for (const [key, value] of Object.entries(metadata)) {
    if (value === undefined) continue;
    if (
      typeof value === "string" ||
      typeof value === "number" ||
      typeof value === "boolean"
    ) {
      attributes[`log.${key}`] = value;
      continue;
    }
    try {
      attributes[`log.${key}`] = JSON.stringify(value);
    } catch {
      attributes[`log.${key}`] = "[unserializable]";
    }
  }

  return attributes;
}

function emitLog(
  scope: string,
  level: LogLevel,
  message: string,
  metadata?: LogMetadata,
  redactKeys: string[] = []
) {
  const attributes = normalizeAttributes(scope, message, metadata);
  const sanitizedAttributes = sanitizeAttributes(attributes, redactKeys);
  recordTelemetryEvent(`log.${scope}`, {
    attributes: sanitizedAttributes,
    level,
  });
}

/**
 * Creates a server logger instance for structured logging via OpenTelemetry.
 *
 * @param scope - Logger scope (e.g., "api.keys", "tools.accommodations")
 * @param options - Optional configuration including redaction keys
 * @returns Logger instance with error, info, and warn methods
 *
 * @example
 * const logger = createServerLogger("api.keys", { redactKeys: ["apiKey"] });
 * logger.info("Key stored", { userId: "123", apiKey: "sk-..." }); // apiKey will be redacted
 */
export function createServerLogger(
  scope: string,
  options: CreateServerLoggerOptions = {}
): ServerLogger {
  const { redactKeys = [] } = options;
  return {
    error: (message, metadata) =>
      emitLog(scope, "error", message, metadata, redactKeys),
    info: (message, metadata) => emitLog(scope, "info", message, metadata, redactKeys),
    warn: (message, metadata) =>
      emitLog(scope, "warning", message, metadata, redactKeys),
  };
}
