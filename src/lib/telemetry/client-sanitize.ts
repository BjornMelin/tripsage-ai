/**
 * @fileoverview Client-side telemetry redaction helpers.
 */

"use client";

import { MAX_ERROR_MESSAGE_LENGTH } from "@/lib/telemetry/constants";

const DEFAULT_ERROR_MESSAGE = "Client error";

const EMAIL_RE = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i;
const JWT_RE = /eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}/;
const LONG_TOKEN_RE = /\b[a-zA-Z0-9_-]{40,}\b/;
const SENSITIVE_MESSAGE_RE =
  /(bearer\s+[^\s]+|authorization\b|api[_-]?key|token|secret|password|session[_-]?id|access[_-]?token|refresh[_-]?token|cookie|set-cookie)/i;

export type SanitizedClientErrorMessage = {
  message: string;
  redacted: boolean;
  truncated: boolean;
};

export function sanitizeClientErrorMessage(
  message: string
): SanitizedClientErrorMessage {
  const trimmed = message.trim();
  if (!trimmed) {
    return { message: DEFAULT_ERROR_MESSAGE, redacted: false, truncated: false };
  }

  if (
    EMAIL_RE.test(trimmed) ||
    JWT_RE.test(trimmed) ||
    LONG_TOKEN_RE.test(trimmed) ||
    SENSITIVE_MESSAGE_RE.test(trimmed)
  ) {
    return { message: DEFAULT_ERROR_MESSAGE, redacted: true, truncated: false };
  }

  const truncated = trimmed.length > MAX_ERROR_MESSAGE_LENGTH;
  const finalMessage = truncated ? trimmed.slice(0, MAX_ERROR_MESSAGE_LENGTH) : trimmed;
  return {
    message: finalMessage,
    redacted: false,
    truncated,
  };
}

export function buildSanitizedErrorForTelemetry(error: Error, message: string): Error {
  const sanitized = new Error(message);
  sanitized.name = error.name;
  if (typeof error.stack === "string") {
    const newlineIndex = error.stack.indexOf("\n");
    sanitized.stack =
      newlineIndex === -1
        ? `${error.name}: ${message}`
        : `${error.name}: ${message}${error.stack.slice(newlineIndex)}`;
  }
  return sanitized;
}
