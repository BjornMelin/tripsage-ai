/**
 * @fileoverview Server-side logging helpers backed by OpenTelemetry.
 */

import "server-only";

import type { TelemetrySpanAttributes } from "@/lib/telemetry/span";
import { recordTelemetryEvent } from "@/lib/telemetry/span";
import {
  MAX_LOG_FIELD_LENGTH,
  REDACTED_VALUE,
  SENSITIVE_METADATA_KEY_RE,
} from "./constants";

type LogLevel = "info" | "warning" | "error";

export type LogMetadata = Record<string, unknown>;

const TRUNCATION_MARKER = " [truncated]";

export interface CreateServerLoggerOptions {
  /**
   * Keys in metadata to redact from telemetry logs.
   * @default []
   */
  redactKeys?: string[];
  /**
   * Redact the primary log message (`log.message`) attribute.
   *
   * Use this for scopes that might accidentally include user input or provider
   * error text in the message parameter. Prefer placing details into metadata
   * fields like `error`/`errorMessage` (which are redacted by default) and keep
   * `message` as a short, non-sensitive summary.
   *
   * @default false
   */
  redactMessage?: boolean;
}

export interface ServerLogger {
  error: (message: string, metadata?: LogMetadata) => void;
  info: (message: string, metadata?: LogMetadata) => void;
  warn: (message: string, metadata?: LogMetadata) => void;
}

function normalizeRedactionKey(key: string): string {
  return key.toLowerCase().replace(/[^a-z0-9]/g, "");
}

function buildRedactionKeySet(redactKeys: string[]): Set<string> {
  return new Set(
    redactKeys.map((key) =>
      normalizeRedactionKey(key.startsWith("log.") ? key.slice("log.".length) : key)
    )
  );
}

function shouldRedactKey(key: string, redactionKeys: Set<string>): boolean {
  const normalized = normalizeRedactionKey(key);
  if (normalized === "error" || normalized === "errormessage") return true;
  return redactionKeys.has(normalized) || SENSITIVE_METADATA_KEY_RE.test(key);
}

function safeJsonStringify(value: unknown, redactionKeys: Set<string>): string {
  try {
    return JSON.stringify(value, (key, nestedValue) => {
      if (!key) return nestedValue;
      if (shouldRedactKey(key, redactionKeys)) return REDACTED_VALUE;
      if (
        typeof nestedValue === "string" &&
        nestedValue.length > MAX_LOG_FIELD_LENGTH
      ) {
        const maxLength = MAX_LOG_FIELD_LENGTH - TRUNCATION_MARKER.length;
        return nestedValue.slice(0, maxLength) + TRUNCATION_MARKER;
      }
      return nestedValue;
    });
  } catch {
    return "[unserializable]";
  }
}

function normalizeAttributes(
  scope: string,
  message: string,
  metadata: LogMetadata | undefined,
  redactionKeys: Set<string>,
  redactMessage: boolean
): TelemetrySpanAttributes {
  const attributes: TelemetrySpanAttributes = {
    "log.message": redactMessage ? REDACTED_VALUE : message,
    "log.scope": scope,
  };

  if (!metadata) {
    return attributes;
  }

  for (const [key, value] of Object.entries(metadata)) {
    if (value === undefined) continue;
    const redacted = shouldRedactKey(key, redactionKeys);
    if (
      typeof value === "string" ||
      typeof value === "number" ||
      typeof value === "boolean"
    ) {
      attributes[`log.${key}`] = redacted ? REDACTED_VALUE : value;
      continue;
    }
    attributes[`log.${key}`] = redacted
      ? REDACTED_VALUE
      : safeJsonStringify(value, redactionKeys);
  }

  return attributes;
}

function emitLog(
  scope: string,
  level: LogLevel,
  message: string,
  metadata?: LogMetadata,
  redactKeys: string[] = [],
  redactMessage = false
) {
  const redactionKeys = buildRedactionKeySet(redactKeys);
  const normalizedAttributes = normalizeAttributes(
    scope,
    message,
    metadata,
    redactionKeys,
    redactMessage
  );
  recordTelemetryEvent(`log.${scope}`, {
    attributes: normalizedAttributes,
    level,
  });
}

/**
 * Creates a server logger instance for structured logging via OpenTelemetry.
 *
 * Metadata is encoded into `log.*` span attributes. Prefer passing primitive values.
 * Non-primitive metadata is JSON-stringified with best-effort redaction for common
 * sensitive keys (e.g., tokens, passwords, API keys). Always avoid passing PII or
 * secrets. Keep `message` as a short, non-sensitive summary; do not include user
 * input or provider error strings in the message text.
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
  const { redactKeys = [], redactMessage = false } = options;
  return {
    error: (message, metadata) =>
      emitLog(scope, "error", message, metadata, redactKeys, redactMessage),
    info: (message, metadata) =>
      emitLog(scope, "info", message, metadata, redactKeys, redactMessage),
    warn: (message, metadata) =>
      emitLog(scope, "warning", message, metadata, redactKeys, redactMessage),
  };
}
