/**
 * @fileoverview Supabase auth error helpers.
 */

import "server-only";

export type SupabaseAuthError = {
  code?: string;
  message?: string;
  status?: number;
};

export function isMfaRequiredError(err: unknown): err is SupabaseAuthError {
  if (!err || typeof err !== "object") {
    return false;
  }

  const { code, message, status } = err as SupabaseAuthError;
  const normalizedCode = typeof code === "string" ? code.toLowerCase() : "";

  if (normalizedCode === "insufficient_aal" || normalizedCode === "mfa_required") {
    return true;
  }

  if (status === 403) {
    const normalized = message?.toLowerCase() ?? "";
    return normalized.includes("mfa") || normalized.includes("aal");
  }

  return false;
}

export function getAuthErrorStatus(err: unknown): number | null {
  if (!err || typeof err !== "object") {
    return null;
  }

  if ("status" in err && typeof err.status === "number") {
    return err.status;
  }

  return null;
}

export function getAuthErrorCode(err: unknown): string | null {
  if (!err || typeof err !== "object") {
    return null;
  }

  if ("code" in err && typeof err.code === "string") {
    return err.code;
  }

  return null;
}
