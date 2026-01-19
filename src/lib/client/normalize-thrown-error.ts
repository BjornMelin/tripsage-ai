/**
 * @fileoverview Client-only helpers for normalizing unknown thrown values into Error instances.
 */

"use client";

import { getErrorMessage } from "react-error-boundary";

export type ErrorWithDigest = Error & { digest?: string };

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object";
}

function getOptionalString(value: unknown, key: string): string | undefined {
  if (!isRecord(value)) return undefined;
  const raw = value[key];
  return typeof raw === "string" && raw.trim().length > 0 ? raw : undefined;
}

export function normalizeThrownError(
  thrown: unknown,
  fallbackMessage = "Unknown error"
): ErrorWithDigest {
  if (thrown instanceof Error) {
    return thrown;
  }

  const message = getErrorMessage(thrown) ?? fallbackMessage;
  const name =
    getOptionalString(thrown, "name") ??
    (typeof thrown === "string" ? "ThrownString" : "NonErrorThrown");

  const error: ErrorWithDigest = new Error(message);
  error.name = name;

  const digest = getOptionalString(thrown, "digest");
  if (digest) {
    error.digest = digest;
  }

  const stack = getOptionalString(thrown, "stack");
  if (stack) {
    error.stack = stack;
  }

  return error;
}
