/**
 * @fileoverview Domain-level errors for accommodation providers and services.
 */

/** Canonical provider error categories used across adapters and services. */
export type ProviderErrorCode =
  | "not_found"
  | "rate_limited"
  | "unauthorized"
  | "provider_failed"
  | "validation_failed"
  | "circuit_open";

/** Optional metadata that helps diagnose provider failures. */
export type ProviderErrorMeta = {
  statusCode?: number;
  retryAfterMs?: number;
  provider?: string;
  operation?: string;
};

/**
 * Normalized error surface for accommodation provider failures.
 *
 * Adapters convert downstream errors into this type so callers can map to
 * tool or domain-specific failures without inspecting raw provider responses.
 */
export class ProviderError extends Error {
  readonly code: ProviderErrorCode;
  readonly statusCode?: number;
  readonly retryAfterMs?: number;
  readonly provider?: string;
  readonly operation?: string;

  constructor(code: ProviderErrorCode, message: string, meta?: ProviderErrorMeta) {
    super(message);
    this.code = code;
    this.statusCode = meta?.statusCode;
    this.retryAfterMs = meta?.retryAfterMs;
    this.provider = meta?.provider;
    this.operation = meta?.operation;
  }
}

export function isProviderError(error: unknown): error is ProviderError {
  return error instanceof ProviderError;
}
