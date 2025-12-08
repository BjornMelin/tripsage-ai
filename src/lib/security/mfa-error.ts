/**
 * @fileoverview Shared MFA error classification and logging helpers.
 */

import type { createServerLogger } from "@/lib/telemetry/logger";

export type MfaErrorClassification = {
  status: number;
  code: string;
  reason: string;
};

/**
 * Classify MFA-related errors into status/code/reason tuples for responses.
 */
export function classifyMfaError(
  error: unknown,
  fallbackCode = "internal_error"
): MfaErrorClassification {
  const message = normalizeMessage(error);

  const statusFromShape = pickStatus(error);
  if (statusFromShape) {
    return {
      code: deriveCode(message) ?? fallbackCode,
      reason: deriveReason(message) ?? "MFA operation failed",
      status: statusFromShape,
    };
  }

  const code = deriveCode(message);
  if (code === "mfa_challenge_failed" || code === "mfa_enroll_failed") {
    return {
      code,
      reason: deriveReason(message) ?? "Invalid MFA request",
      status: 400,
    };
  }

  const normalized = message.toLowerCase();

  if (normalized.includes("rate limit")) {
    return {
      code: "rate_limited",
      reason: "Rate limit exceeded",
      status: 429,
    };
  }

  if (normalized.includes("not found") || normalized.includes("invalid factor")) {
    return {
      code: "mfa_factor_not_found",
      reason: "Factor not found",
      status: 404,
    };
  }

  return {
    code: code ?? fallbackCode,
    reason: deriveReason(message) ?? "MFA operation failed",
    status: 500,
  };
}

/**
 * Log MFA errors with sanitized metadata. Avoids passing raw error objects to the
 * logger; uses message/code/status plus selected context fields.
 */
export function logMfaError(
  logger: ReturnType<typeof createServerLogger>,
  error: unknown,
  context?: Record<string, unknown>,
  fallbackCode = "internal_error"
): void {
  const { status, code, reason } = classifyMfaError(error, fallbackCode);
  const message = normalizeMessage(error);
  logger.error("mfa error", {
    code,
    errorMessage: message,
    reason,
    status,
    ...sanitizeContext(context),
  });
}

function sanitizeContext(context?: Record<string, unknown>): Record<string, unknown> {
  if (!context) return {};
  const allowedKeys = ["userId", "factorId", "challengeId", "scope", "operation"];
  const safe: Record<string, unknown> = {};
  for (const key of allowedKeys) {
    if (key in context) {
      safe[key] = context[key];
    }
  }
  return safe;
}

function pickStatus(error: unknown): number | undefined {
  const candidates = [
    (error as { status?: number })?.status,
    (error as { statusCode?: number })?.statusCode,
    (error as { httpStatus?: number })?.httpStatus,
  ].filter(
    (value): value is number => typeof value === "number" && value >= 400 && value < 600
  );
  return candidates[0];
}

function deriveCode(message: string): string | undefined {
  const normalized = message.toLowerCase();
  if (normalized.includes("mfa_challenge_failed")) return "mfa_challenge_failed";
  if (normalized.includes("mfa_enroll_failed")) return "mfa_enroll_failed";
  if (normalized.includes("mfa_enrollment_store_failed"))
    return "mfa_enrollment_store_failed";
  if (normalized.includes("mfa_enrollment_expire_failed"))
    return "mfa_enrollment_expire_failed";
  if (
    normalized.includes("factor not found") ||
    normalized.includes("invalid factor")
  ) {
    return "mfa_factor_not_found";
  }
  if (normalized.includes("rate limit")) return "rate_limited";
  return undefined;
}

function deriveReason(message: string): string | undefined {
  const normalized = message.toLowerCase();
  if (normalized.includes("mfa_challenge_failed")) return "Invalid factor or challenge";
  if (normalized.includes("mfa_enroll_failed")) return "Failed to enroll MFA factor";
  if (normalized.includes("mfa_enrollment_store_failed"))
    return "Failed to persist enrollment";
  if (normalized.includes("mfa_enrollment_expire_failed"))
    return "Failed to expire prior enrollments";
  if (normalized.includes("rate limit")) return "Rate limit exceeded";
  if (normalized.includes("not found") || normalized.includes("invalid factor"))
    return "Factor not found";
  return undefined;
}

function normalizeMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return String(error ?? "");
}
