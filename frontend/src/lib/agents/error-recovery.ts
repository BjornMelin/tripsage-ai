/**
 * @fileoverview Error recovery adapter for agent tool execution.
 *
 * Maps common tool/HTTP errors to user-friendly messages and provides
 * error handlers for AI SDK streaming responses.
 */

/**
 * Common error codes from agent tool execution.
 */
export enum AgentErrorCode {
  RateLimitExceeded = "rate_limit_exceeded",
  Unauthorized = "unauthorized",
  ValidationError = "validation_error",
  ToolNotFound = "tool_not_found",
  ToolExecutionFailed = "tool_execution_failed",
  ProviderError = "provider_error",
  NetworkError = "network_error",
  Timeout = "timeout",
  Unknown = "unknown",
}

/**
 * Map error to user-friendly message.
 *
 * Analyzes error message and type to determine appropriate user-facing
 * message. Returns a concise, actionable message.
 *
 * @param error Error instance or message string.
 * @returns User-friendly error message.
 */
export function mapErrorToMessage(error: unknown): string {
  const message = error instanceof Error ? error.message : String(error);
  const lowerMessage = message.toLowerCase();

  if (lowerMessage.includes("rate limit") || lowerMessage.includes("rate_limit")) {
    return "Rate limit exceeded. Please wait a moment and try again.";
  }

  if (
    lowerMessage.includes("unauthorized") ||
    lowerMessage.includes("401") ||
    lowerMessage.includes("403")
  ) {
    return "Authentication required. Please sign in and try again.";
  }

  if (
    lowerMessage.includes("validation") ||
    lowerMessage.includes("invalid") ||
    lowerMessage.includes("400")
  ) {
    return "Invalid request. Please check your input and try again.";
  }

  if (lowerMessage.includes("timeout") || lowerMessage.includes("timed out")) {
    return "Request timed out. Please try again.";
  }

  if (
    lowerMessage.includes("network") ||
    lowerMessage.includes("fetch") ||
    lowerMessage.includes("connection")
  ) {
    return "Network error. Please check your connection and try again.";
  }

  if (lowerMessage.includes("tool") && lowerMessage.includes("not found")) {
    return "Tool not available. Please try a different request.";
  }

  if (lowerMessage.includes("provider") || lowerMessage.includes("api")) {
    return "Service temporarily unavailable. Please try again later.";
  }

  return "An error occurred. Please try again or contact support if the problem persists.";
}

/**
 * Create error handler for AI SDK streaming responses.
 *
 * Returns a function that maps errors to user-friendly messages for
 * display in the UI.
 *
 * @returns Error handler function for use with toUIMessageStreamResponse.
 */
export function createErrorHandler(): (error: unknown) => string {
  return (error: unknown) => {
    return mapErrorToMessage(error);
  };
}
