/**
 * @fileoverview Error type definitions and helpers for API and React Query
 * integration. Includes rich error classes, guards, and user-facing messages.
 */

export interface ApiErrorResponse {
  message: string;
  status: number;
  code?: string;
  details?: Record<string, unknown>;
  timestamp?: string;
  path?: string;
}

/**
 * Standard API error class with enhanced error information
 */
export class ApiError extends Error {
  public readonly status: number;
  public readonly code?: string;
  public readonly details?: Record<string, unknown>;
  public readonly timestamp: string;
  public readonly path?: string;

  constructor(response: ApiErrorResponse) {
    super(response.message);
    this.name = "ApiError";
    this.status = response.status;
    this.code = response.code;
    this.details = response.details;
    this.timestamp = response.timestamp || new Date().toISOString();
    this.path = response.path;

    // Ensure proper prototype chain
    Object.setPrototypeOf(this, ApiError.prototype);
  }

  /**
   * Check if this is a client error (4xx)
   */
  get isClientError(): boolean {
    return this.status >= 400 && this.status < 500;
  }

  /**
   * Check if this is a server error (5xx)
   */
  get isServerError(): boolean {
    return this.status >= 500;
  }

  /**
   * Check if this error should be retried
   */
  get shouldRetry(): boolean {
    return this.isServerError || this.status === 408 || this.status === 429;
  }

  /**
   * Get user-friendly error message
   */
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
   * Convert to JSON for logging
   */
  toJSON() {
    return {
      name: this.name,
      message: this.message,
      status: this.status,
      code: this.code,
      details: this.details,
      timestamp: this.timestamp,
      path: this.path,
      stack: this.stack,
    };
  }
}

/**
 * Network-specific error for connection issues
 */
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

/**
 * Timeout error for request timeouts
 */
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

/**
 * Validation error for form/input validation
 */
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

/**
 * Type guards for error identification
 */
export const isApiError = (error: unknown): error is ApiError => {
  return error instanceof ApiError;
};

export const isNetworkError = (error: unknown): error is NetworkError => {
  return (
    error instanceof NetworkError ||
    (error instanceof Error && "isNetworkError" in error)
  );
};

export const isTimeoutError = (error: unknown): error is TimeoutError => {
  return (
    error instanceof TimeoutError ||
    (error instanceof Error && "isTimeoutError" in error)
  );
};

export const isValidationError = (error: unknown): error is ValidationError => {
  return (
    error instanceof ValidationError ||
    (error instanceof Error && "isValidationError" in error)
  );
};

/**
 * Union type for all possible errors
 */
export type AppError = ApiError | NetworkError | TimeoutError | ValidationError;

/**
 * Error handler utility for React Query
 */
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
      return new ApiError({
        message: error.message,
        status: error.status,
        code: "code" in error ? String(error.code) : undefined,
      });
    }

    // Default to network error for generic errors
    return new NetworkError(error.message);
  }

  // Fallback for unknown error types
  return new NetworkError("An unknown error occurred");
};

/**
 * Error boundary helper for React Query errors
 */
export const getErrorMessage = (error: unknown): string => {
  const handledError = handleApiError(error);
  return handledError.userMessage;
};

/**
 * Check if an error should trigger a retry
 */
export const shouldRetryError = (error: unknown): boolean => {
  const handledError = handleApiError(error);
  return "shouldRetry" in handledError ? handledError.shouldRetry : false;
};
