/**
 * @fileoverview Shared telemetry constants.
 */

/** Canonical tracer/service name for frontend observability. */
export const TELEMETRY_SERVICE_NAME = "tripsage-frontend";

/** Whether to suppress console output in telemetry alerts (for performance tests). */
export const TELEMETRY_SILENT = process.env.NEXT_PUBLIC_TELEMETRY_SILENT === "1";

/** Maximum length for error messages in telemetry (truncate beyond this). */
export const MAX_ERROR_MESSAGE_LENGTH = 200;

/** Maximum length for individual log field values before truncation with marker. */
export const MAX_LOG_FIELD_LENGTH = 500;

/** Placeholder value for redacted sensitive data in telemetry. */
export const REDACTED_VALUE = "[REDACTED]";

/** Regex pattern to identify sensitive metadata keys that should be redacted. */
export const SENSITIVE_METADATA_KEY_RE =
  /(token|secret|password|api[_-]?key|authorization|cookie|set-cookie|email|user[_-]?id|session[_-]?id|access[_-]?token|refresh[_-]?token)/i;
