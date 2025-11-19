/**
 * @fileoverview Type definitions and error classes for Expedia Rapid API client.
 *
 * Defines custom error types and request context structures used by the
 * Expedia client for API communication and error handling.
 */

/**
 * Error class for Expedia Rapid API operations.
 *
 * Extends Error with structured error information including API error codes,
 * HTTP status codes, and additional context details.
 */
export class ExpediaApiError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly statusCode?: number,
    public readonly details?: Record<string, unknown>
  ) {
    super(message);
    this.name = "ExpediaApiError";
  }
}

/**
 * Context information for Expedia API requests.
 *
 * Provides customer-specific parameters for tracking, testing, and localization.
 */
export type ExpediaRequestContext = {
  customerIp?: string;
  customerSessionId?: string;
  testScenario?: string;
  userAgent?: string;
};
