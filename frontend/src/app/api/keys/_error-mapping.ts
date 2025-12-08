import { errorResponse } from "@/lib/api/route-helpers";

export const PLANNED_ERROR_CODES = {
  invalidKey: "INVALID_KEY",
  networkError: "NETWORK_ERROR",
  vaultUnavailable: "VAULT_UNAVAILABLE",
} as const;

export type PlannedErrorCode =
  (typeof PLANNED_ERROR_CODES)[keyof typeof PLANNED_ERROR_CODES];

export function vaultUnavailableResponse(reason: string, err?: unknown): Response {
  return errorResponse({
    err,
    error: PLANNED_ERROR_CODES.vaultUnavailable,
    reason,
    status: 500,
  });
}

export function mapProviderStatusToCode(status: number): PlannedErrorCode {
  if (status === 429) return PLANNED_ERROR_CODES.networkError;
  if (status >= 500) return PLANNED_ERROR_CODES.networkError;
  if (status >= 400) return PLANNED_ERROR_CODES.invalidKey;
  return PLANNED_ERROR_CODES.networkError;
}

export function mapProviderExceptionToCode(_error: unknown): PlannedErrorCode {
  return PLANNED_ERROR_CODES.networkError;
}
