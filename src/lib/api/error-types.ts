/**
 * @fileoverview Error type definitions and helpers for API and React Query
 * integration. Includes rich error classes, guards, and user-facing messages.
 */

/** API error response interface. */
export interface ApiErrorResponse {
  message: string;
  status: number;
  code?: string;
  details?: Record<string, unknown>;
  timestamp?: string;
  path?: string;
}

/** Validation result type for API errors. */
export interface ValidationResult<T> {
  success: boolean;
  errors?: Array<{
    code: string;
    context: string;
    field?: string;
    message: string;
    path?: string[];
    timestamp: Date;
    value?: T;
  }>;
}

/**
 * Standard API error class with enhanced error information.
 * Supports validation errors and structured error details.
 */
export class ApiError extends Error {
  public readonly status: number;
  public readonly code?: string;
  public readonly details?: Record<string, unknown>;
  public readonly timestamp: string;
  public readonly path?: string;
  public readonly validationErrors?: ValidationResult<unknown>;
  public readonly data?: unknown;
  public readonly endpoint?: string;

  constructor(
    messageOrOptions:
      | string
      | {
          code?: string;
          data?: unknown;
          endpoint?: string;
          message: string;
          status: number;
          validationErrors?: ValidationResult<unknown>;
        },
    statusArg?: number,
    code?: string,
    data?: unknown,
    endpoint?: string,
    validationErrors?: ValidationResult<unknown>
  ) {
    const options =
      typeof messageOrOptions === "string"
        ? {
            code,
            data,
            endpoint,
            message: messageOrOptions,
            status: statusArg ?? 500,
            validationErrors,
          }
        : messageOrOptions;

    super(options.message);
    this.name = "ApiError";
    this.status = options.status;
    this.code = options.code;
    this.data = options.data;
    this.endpoint = options.endpoint;
    this.validationErrors = options.validationErrors;
    this.timestamp = new Date().toISOString();

    // Ensure proper prototype chain
    Object.setPrototypeOf(this, ApiError.prototype);
  }

  /** Check if this is a client error (4xx). */
  get isClientError(): boolean {
    return this.status >= 400 && this.status < 500;
  }

  /** Check if this is a server error (5xx). */
  get isServerError(): boolean {
    return this.status >= 500;
  }

  /** Check if this error should be retried. */
  get shouldRetry(): boolean {
    return this.isServerError || this.status === 408 || this.status === 429;
  }

  /** Get user-friendly error message. */
  get userMessage(): string {
    if (this.status === 401) return "Authentication required. Please log in.";
    if (this.status === 403) return "You don't have permission to perform this action.";
    if (this.status === 404) return "The requested resource was not found.";
    if (this.status === 422) return "Invalid data provided. Please check your input.";
    if (this.status === 429) return "Too many requests. Please try again later.";
    if (this.isServerError) return "Server error. Please try again later.";
    return this.message;
  }

  /**
   * Checks if this error was caused by validation failures.
   *
   * @returns True if the error contains validation errors.
   */
  public isValidationError(): boolean {
    return Boolean(this.validationErrors && !this.validationErrors.success);
  }

  /**
   * Extracts validation error messages from the error.
   *
   * @returns Array of validation error messages, or empty array if none.
   */
  public getValidationErrors(): string[] {
    if (!this.validationErrors || this.validationErrors.success) {
      return [];
    }
    return this.validationErrors.errors?.map((err) => err.message) || [];
  }

  /** Convert to JSON for logging */
  // biome-ignore lint/style/useNamingConvention: Standard JSON serialization method
  toJSON() {
    return {
      code: this.code,
      details: this.details,
      endpoint: this.endpoint,
      message: this.message,
      name: this.name,
      path: this.path,
      stack: this.stack,
      status: this.status,
      timestamp: this.timestamp,
      validationErrors: this.getValidationErrors(),
    };
  }
}

/** Network-specific error for connection issues. */
export class NetworkError extends Error {
  public readonly isNetworkError = true;

  constructor(message = "Network error occurred") {
    super(message);
    this.name = "NetworkError";
    Object.setPrototypeOf(this, NetworkError.prototype);
  }

  get shouldRetry(): boolean {
    return true;
  }

  get userMessage(): string {
    return "Connection error. Please check your internet connection and try again.";
  }
}

/** Timeout error for request timeouts. */
export class TimeoutError extends Error {
  public readonly isTimeoutError = true;

  constructor(message = "Request timed out") {
    super(message);
    this.name = "TimeoutError";
    Object.setPrototypeOf(this, TimeoutError.prototype);
  }

  get shouldRetry(): boolean {
    return true;
  }

  get userMessage(): string {
    return "Request timed out. Please try again.";
  }
}

/** Validation error for form/input validation. */
export class ValidationError extends Error {
  public readonly isValidationError = true;
  public readonly errors: Record<string, string[]>;

  constructor(message: string, errors: Record<string, string[]> = {}) {
    super(message);
    this.name = "ValidationError";
    this.errors = errors;
    Object.setPrototypeOf(this, ValidationError.prototype);
  }

  get shouldRetry(): boolean {
    return false;
  }

  get userMessage(): string {
    const firstError = Object.values(this.errors)[0]?.[0];
    return firstError || this.message;
  }
}

/** Type guards for error identification. */
export const isApiError = (error: unknown): error is ApiError => {
  return error instanceof ApiError;
};

/** Check if an error is a network error. */
export const isNetworkError = (error: unknown): error is NetworkError => {
  return (
    error instanceof NetworkError ||
    (error instanceof Error && "isNetworkError" in error)
  );
};

/** Check if an error is a timeout error. */
export const isTimeoutError = (error: unknown): error is TimeoutError => {
  return (
    error instanceof TimeoutError ||
    (error instanceof Error && "isTimeoutError" in error)
  );
};

/** Check if an error is a validation error. */
export const isValidationError = (error: unknown): error is ValidationError => {
  return (
    error instanceof ValidationError ||
    (error instanceof Error && "isValidationError" in error)
  );
};

/** Union type for all possible errors. */
export type AppError = ApiError | NetworkError | TimeoutError | ValidationError;

/** Error handler utility for React Query. */
export const handleApiError = (error: unknown): AppError => {
  if (
    isApiError(error) ||
    isNetworkError(error) ||
    isTimeoutError(error) ||
    isValidationError(error)
  ) {
    return error;
  }

  if (error instanceof Error) {
    // Try to parse as API error if it has status
    if ("status" in error && typeof error.status === "number") {
      const status = error.status as number;
      const code = "code" in error ? String(error.code) : undefined;
      const data = "data" in error ? error.data : undefined;
      const endpoint = "endpoint" in error ? String(error.endpoint) : undefined;
      const validationErrors =
        "validationErrors" in error
          ? (error.validationErrors as ValidationResult<unknown>)
          : undefined;
      return new ApiError(
        error.message,
        status,
        code,
        data,
        endpoint,
        validationErrors
      );
    }

    // Default to network error for generic errors
    return new NetworkError(error.message);
  }

  // Fallback for unknown error types
  return new NetworkError("An unknown error occurred");
};

/** Error boundary helper for React Query errors */
export const getErrorMessage = (error: unknown): string => {
  const handledError = handleApiError(error);
  return handledError.userMessage;
};

/** Check if an error should trigger a retry */
export const shouldRetryError = (error: unknown): boolean => {
  const handledError = handleApiError(error);
  return "shouldRetry" in handledError ? handledError.shouldRetry : false;
};
