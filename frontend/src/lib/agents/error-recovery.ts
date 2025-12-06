/**
 * @fileoverview Error recovery adapter for agent tool execution.
 *
 * Maps common tool/HTTP errors to user-friendly messages and provides
 * error handlers for AI SDK v6 streaming responses.
 *
 * Handles AI SDK specific errors:
 * - NoSuchToolError: Model tried to call an unknown tool
 * - InvalidToolInputError: Model provided invalid tool arguments
 */

import { InvalidToolInputError, NoSuchToolError } from "ai";

/**
 * Common error codes from agent tool execution.
 */
export enum AgentErrorCode {
  RateLimitExceeded = "rate_limit_exceeded",
  Unauthorized = "unauthorized",
  ValidationError = "validation_error",
  ToolNotFound = "tool_not_found",
  InvalidToolInput = "invalid_tool_input",
  ToolExecutionFailed = "tool_execution_failed",
  ProviderError = "provider_error",
  NetworkError = "network_error",
  Timeout = "timeout",
  Unknown = "unknown",
}

function detectErrorType(message: string): AgentErrorCode | null {
  const lowerMessage = message.toLowerCase();

  if (lowerMessage.includes("rate limit") || lowerMessage.includes("rate_limit")) {
    return AgentErrorCode.RateLimitExceeded;
  }

  if (
    lowerMessage.includes("unauthorized") ||
    lowerMessage.includes("401") ||
    lowerMessage.includes("403")
  ) {
    return AgentErrorCode.Unauthorized;
  }

  if (
    lowerMessage.includes("validation") ||
    lowerMessage.includes("invalid") ||
    lowerMessage.includes("400")
  ) {
    return AgentErrorCode.ValidationError;
  }

  if (lowerMessage.includes("timeout") || lowerMessage.includes("timed out")) {
    return AgentErrorCode.Timeout;
  }

  if (
    lowerMessage.includes("network") ||
    lowerMessage.includes("fetch") ||
    lowerMessage.includes("connection")
  ) {
    return AgentErrorCode.NetworkError;
  }

  if (
    lowerMessage.includes("tool") &&
    (lowerMessage.includes("not found") || lowerMessage.includes("unknown"))
  ) {
    return AgentErrorCode.ToolNotFound;
  }

  if (lowerMessage.includes("provider") || lowerMessage.includes("api")) {
    return AgentErrorCode.ProviderError;
  }

  return null;
}

/**
 * Map error to user-friendly message.
 *
 * Analyzes error message and type to determine appropriate user-facing
 * message. Handles AI SDK v6 specific errors (NoSuchToolError, InvalidToolInputError).
 *
 * @param error Error instance or message string.
 * @returns User-friendly error message.
 */
export function mapErrorToMessage(error: unknown): string {
  // Handle AI SDK v6 specific errors first
  if (NoSuchToolError.isInstance(error)) {
    return "The assistant tried to use an unavailable tool. Please try rephrasing your request.";
  }

  if (InvalidToolInputError.isInstance(error)) {
    return "The assistant provided invalid parameters. Please try again with a clearer request.";
  }

  const message = error instanceof Error ? error.message : String(error);
  const detected = detectErrorType(message);

  switch (detected) {
    case AgentErrorCode.RateLimitExceeded:
      return "Rate limit exceeded. Please wait a moment and try again.";
    case AgentErrorCode.Unauthorized:
      return "Authentication required. Please sign in and try again.";
    case AgentErrorCode.ValidationError:
      return "Invalid request. Please check your input and try again.";
    case AgentErrorCode.Timeout:
      return "Request timed out. Please try again.";
    case AgentErrorCode.NetworkError:
      return "Network error. Please check your connection and try again.";
    case AgentErrorCode.ToolExecutionFailed:
      return "Tool not available. Please try a different request.";
    case AgentErrorCode.ProviderError:
      return "Service temporarily unavailable. Please try again later.";
    default:
      break;
  }

  return "An error occurred. Please try again or contact support if the problem persists.";
}

/**
 * Classify error into AgentErrorCode.
 *
 * Used for telemetry and error tracking.
 *
 * @param error Error to classify.
 * @returns AgentErrorCode classification.
 */
export function classifyError(error: unknown): AgentErrorCode {
  if (NoSuchToolError.isInstance(error)) {
    return AgentErrorCode.ToolNotFound;
  }

  if (InvalidToolInputError.isInstance(error)) {
    return AgentErrorCode.InvalidToolInput;
  }

  const message = error instanceof Error ? error.message : String(error);
  const detected = detectErrorType(message);

  return detected ?? AgentErrorCode.Unknown;
}

/**
 * Create error handler for AI SDK v6 streaming responses.
 *
 * Returns a function that maps errors to user-friendly messages for
 * display in the UI. Handles AI SDK specific errors (NoSuchToolError,
 * InvalidToolInputError) as well as common HTTP/network errors.
 *
 * @returns Error handler function for use with toUIMessageStreamResponse.
 *
 * @example
 * ```typescript
 * const result = streamText({
 *   model: provider.model,
 *   messages: convertToModelMessages(messages),
 *   tools: myTools,
 * });
 *
 * return result.toUIMessageStreamResponse({
 *   onError: createErrorHandler(),
 * });
 * ```
 */
export function createErrorHandler(): (error: unknown) => string {
  return mapErrorToMessage;
}

/**
 * Create error handler with telemetry callback.
 *
 * Logs errors to telemetry before returning user-friendly message.
 *
 * @param onError Optional callback for telemetry/logging.
 * @returns Error handler function.
 *
 * @example
 * ```typescript
 * return result.toUIMessageStreamResponse({
 *   onError: createErrorHandlerWithTelemetry((error, code) => {
 *     logger.error('Stream error', { code, error: String(error) });
 *   }),
 * });
 * ```
 */
export function createErrorHandlerWithTelemetry(
  onError?: (error: unknown, code: AgentErrorCode) => void
): (error: unknown) => string {
  return (error: unknown) => {
    const code = classifyError(error);
    onError?.(error, code);
    return mapErrorToMessage(error);
  };
}
