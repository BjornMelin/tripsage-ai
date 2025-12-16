/**
 * @fileoverview Consolidated error types for API and React Query integration.
 * Single ApiError class with error codes replaces separate error classes.
 */

/** Standard error codes for API errors. */
export type ApiErrorCode =
  | "NETWORK_ERROR"
  | "TIMEOUT_ERROR"
  | "VALIDATION_ERROR"
  | "REQUEST_CANCELLED"
  | "UNAUTHORIZED"
  | "FORBIDDEN"
  | "NOT_FOUND"
  | "RATE_LIMITED"
  | "SERVER_ERROR"
  | "UNKNOWN_ERROR"
  | string; // Allow custom codes like HTTP_xxx

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

/** Field-level validation errors for form validation. */
export type FieldValidationErrors = Record<string, string[]>;

/**
 * Unified API error class with error codes.
 * Replaces separate NetworkError, TimeoutError, ValidationError classes.
 */
export class ApiError extends Error {
  public readonly status: number;
  public readonly code: ApiErrorCode;
  public readonly details?: Record<string, unknown>;
  public readonly timestamp: string;
  public readonly path?: string;
  public readonly validationErrors?: ValidationResult<unknown>;
  public readonly fieldErrors?: FieldValidationErrors;
  public readonly data?: unknown;
  public readonly endpoint?: string;

  constructor(
    messageOrOptions:
      | string
      | {
          code?: ApiErrorCode;
          data?: unknown;
          endpoint?: string;
          fieldErrors?: FieldValidationErrors;
          message: string;
          status: number;
          validationErrors?: ValidationResult<unknown>;
        },
    statusArg?: number,
    code?: ApiErrorCode,
    data?: unknown,
    endpoint?: string,
    validationErrors?: ValidationResult<unknown>,
    fieldErrors?: FieldValidationErrors
  ) {
    const options =
      typeof messageOrOptions === "string"
        ? {
            code,
            data,
            endpoint,
            fieldErrors,
            message: messageOrOptions,
            status: statusArg ?? 500,
            validationErrors,
          }
        : messageOrOptions;

    super(options.message);
    this.name = "ApiError";
    this.status = options.status;
    this.code = options.code ?? ApiError.codeFromStatus(options.status);
    this.data = options.data;
    this.endpoint = options.endpoint;
    this.validationErrors = options.validationErrors;
    this.fieldErrors = options.fieldErrors;
    this.timestamp = new Date().toISOString();

    Object.setPrototypeOf(this, ApiError.prototype);
  }

  /** Derive error code from HTTP status. */
  private static codeFromStatus(status: number): ApiErrorCode {
    if (status === 0) return "NETWORK_ERROR";
    if (status === 401) return "UNAUTHORIZED";
    if (status === 403) return "FORBIDDEN";
    if (status === 404) return "NOT_FOUND";
    if (status === 408) return "TIMEOUT_ERROR";
    if (status === 422) return "VALIDATION_ERROR";
    if (status === 429) return "RATE_LIMITED";
    if (status >= 500) return "SERVER_ERROR";
    return "UNKNOWN_ERROR";
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
    return (
      this.code === "NETWORK_ERROR" ||
      this.code === "TIMEOUT_ERROR" ||
      this.code === "SERVER_ERROR" ||
      this.code === "RATE_LIMITED"
    );
  }

  /** Get user-friendly error message. */
  get userMessage(): string {
    switch (this.code) {
      case "NETWORK_ERROR":
        return "Connection error. Please check your internet connection and try again.";
      case "TIMEOUT_ERROR":
        return "Request timed out. Please try again.";
      case "UNAUTHORIZED":
        return "Authentication required. Please log in.";
      case "FORBIDDEN":
        return "You don't have permission to perform this action.";
      case "NOT_FOUND":
        return "The requested resource was not found.";
      case "VALIDATION_ERROR":
        return this.getFirstFieldError() || "Invalid data provided. Please check your input.";
      case "RATE_LIMITED":
        return "Too many requests. Please try again later.";
      case "SERVER_ERROR":
        return "Server error. Please try again later.";
      default:
        return this.message;
    }
  }

  /** Get first field error message if available. */
  private getFirstFieldError(): string | undefined {
    if (this.fieldErrors) {
      const firstError = Object.values(this.fieldErrors)[0]?.[0];
      if (firstError) return firstError;
    }
    return undefined;
  }

  /** Checks if this error was caused by validation failures. */
  public isValidationError(): boolean {
    return (
      this.code === "VALIDATION_ERROR" ||
      Boolean(this.validationErrors && !this.validationErrors.success) ||
      Boolean(this.fieldErrors && Object.keys(this.fieldErrors).length > 0)
    );
  }

  /** Extracts validation error messages from the error. */
  public getValidationErrors(): string[] {
    const errors: string[] = [];
    if (this.validationErrors?.errors) {
      errors.push(...this.validationErrors.errors.map((err) => err.message));
    }
    if (this.fieldErrors) {
      errors.push(...Object.values(this.fieldErrors).flat());
    }
    return errors;
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

  /** Factory for network errors. */
  static network(message = "Network error occurred"): ApiError {
    return new ApiError({ message, status: 0, code: "NETWORK_ERROR" });
  }

  /** Factory for timeout errors. */
  static timeout(message = "Request timed out"): ApiError {
    return new ApiError({ message, status: 408, code: "TIMEOUT_ERROR" });
  }

  /** Factory for validation errors. */
  static validation(
    message: string,
    fieldErrors?: FieldValidationErrors
  ): ApiError {
    return new ApiError({
      message,
      status: 422,
      code: "VALIDATION_ERROR",
      fieldErrors,
    });
  }
}

/** Type guard for ApiError. */
export const isApiError = (error: unknown): error is ApiError => {
  return error instanceof ApiError;
};

/** Check if an error is a network error (code-based). */
export const isNetworkError = (error: unknown): error is ApiError => {
  return (
    (error instanceof ApiError && error.code === "NETWORK_ERROR") ||
    (error instanceof Error && error.name === "NetworkError")
  );
};

/** Check if an error is a timeout error (code-based). */
export const isTimeoutError = (error: unknown): error is ApiError => {
  return (
    (error instanceof ApiError && error.code === "TIMEOUT_ERROR") ||
    (error instanceof Error && error.name === "TimeoutError")
  );
};

/** Check if an error is a validation error (code-based). */
export const isValidationErrorGuard = (error: unknown): error is ApiError => {
  return (
    (error instanceof ApiError && error.code === "VALIDATION_ERROR") ||
    (error instanceof ApiError && error.isValidationError())
  );
};

/** Union type for app errors (now just ApiError). */
export type AppError = ApiError;

/** Error handler utility - normalizes all errors to ApiError. */
export const handleApiError = (error: unknown): ApiError => {
  if (error instanceof ApiError) {
    return error;
  }

  if (error instanceof Error) {
    // Check for network/timeout by name (legacy compatibility)
    if (error.name === "NetworkError") {
      return ApiError.network(error.message);
    }
    if (error.name === "TimeoutError") {
      return ApiError.timeout(error.message);
    }
    if (error.name === "AbortError") {
      return new ApiError({
        message: "Request was cancelled",
        status: 0,
        code: "REQUEST_CANCELLED",
      });
    }

    // Try to parse as API error if it has status
    if ("status" in error && typeof error.status === "number") {
      const status = error.status as number;
      const code = "code" in error ? (error.code as ApiErrorCode) : undefined;
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
    return ApiError.network(error.message);
  }

  // Fallback for unknown error types
  return ApiError.network("An unknown error occurred");
};

/** Error boundary helper for React Query errors */
export const getErrorMessage = (error: unknown): string => {
  const handledError = handleApiError(error);
  return handledError.userMessage;
};

/** Check if an error should trigger a retry */
export const shouldRetryError = (error: unknown): boolean => {
  const handledError = handleApiError(error);
  return handledError.shouldRetry;
};
