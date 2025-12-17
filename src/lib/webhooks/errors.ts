/**
 * @fileoverview Typed webhook errors with explicit HTTP status mapping.
 */

import "server-only";

/**
 * Stable, public webhook error codes.
 *
 * Note: not every code is produced by the shared handler today; some are reserved
 * for webhook-specific implementations that throw a more precise typed error.
 *
 * `DUPLICATE` is used for internal classification/telemetry. HTTP responses for
 * duplicate events return `{ ok: true, duplicate: true }` with status 200 and no
 * explicit `code` field.
 */
export type WebhookErrorCode =
  | "VALIDATION_ERROR"
  | "UNAUTHORIZED"
  | "NOT_FOUND"
  | "CONFLICT"
  | "DUPLICATE"
  | "RATE_LIMITED"
  | "SERVICE_UNAVAILABLE"
  | "UPSTREAM_ERROR"
  | "TIMEOUT"
  | "UNKNOWN";

export class WebhookError extends Error {
  readonly code: WebhookErrorCode;
  readonly status: number;
  readonly retryAfterSeconds: number | null;

  constructor(
    message: string,
    options: {
      code: WebhookErrorCode;
      status: number;
      retryAfterSeconds?: number | null;
      cause?: unknown;
    }
  ) {
    super(message, { cause: options.cause });
    this.name = "WebhookError";
    this.code = options.code;
    this.status = options.status;
    this.retryAfterSeconds = options.retryAfterSeconds ?? null;
  }
}

export class WebhookValidationError extends WebhookError {
  constructor(message: string = "invalid_request", options?: { cause?: unknown }) {
    super(message, { cause: options?.cause, code: "VALIDATION_ERROR", status: 400 });
    this.name = "WebhookValidationError";
  }
}

export class WebhookUnauthorizedError extends WebhookError {
  constructor(message: string = "unauthorized", options?: { cause?: unknown }) {
    super(message, { cause: options?.cause, code: "UNAUTHORIZED", status: 401 });
    this.name = "WebhookUnauthorizedError";
  }
}

export class WebhookNotFoundError extends WebhookError {
  constructor(message: string = "not_found", options?: { cause?: unknown }) {
    super(message, { cause: options?.cause, code: "NOT_FOUND", status: 404 });
    this.name = "WebhookNotFoundError";
  }
}

export class WebhookConflictError extends WebhookError {
  constructor(message: string = "conflict", options?: { cause?: unknown }) {
    super(message, { cause: options?.cause, code: "CONFLICT", status: 409 });
    this.name = "WebhookConflictError";
  }
}

export class WebhookDuplicateError extends WebhookError {
  constructor(message: string = "duplicate", options?: { cause?: unknown }) {
    super(message, { cause: options?.cause, code: "DUPLICATE", status: 200 });
    this.name = "WebhookDuplicateError";
  }
}

export class WebhookRateLimitedError extends WebhookError {
  constructor(
    message: string = "rate_limit_exceeded",
    options?: { cause?: unknown; retryAfterSeconds?: number | null }
  ) {
    super(message, {
      cause: options?.cause,
      code: "RATE_LIMITED",
      retryAfterSeconds: options?.retryAfterSeconds ?? null,
      status: 429,
    });
    this.name = "WebhookRateLimitedError";
  }
}

export class WebhookServiceUnavailableError extends WebhookError {
  constructor(message: string = "service_unavailable", options?: { cause?: unknown }) {
    super(message, {
      cause: options?.cause,
      code: "SERVICE_UNAVAILABLE",
      status: 503,
    });
    this.name = "WebhookServiceUnavailableError";
  }
}

export class WebhookUpstreamError extends WebhookError {
  constructor(message: string = "upstream_error", options?: { cause?: unknown }) {
    super(message, { cause: options?.cause, code: "UPSTREAM_ERROR", status: 502 });
    this.name = "WebhookUpstreamError";
  }
}

export class WebhookTimeoutError extends WebhookError {
  constructor(message: string = "timeout", options?: { cause?: unknown }) {
    super(message, { cause: options?.cause, code: "TIMEOUT", status: 504 });
    this.name = "WebhookTimeoutError";
  }
}
