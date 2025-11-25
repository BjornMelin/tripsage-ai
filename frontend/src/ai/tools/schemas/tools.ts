/**
 * @fileoverview Zod v4 schemas for tool execution, travel advisory, and error handling.
 */

import { z } from "zod";

/** Zod schema for travel advisory safety category. */
export const safetyCategorySchema = z.object({
  category: z.string(),
  description: z.string().optional(),
  value: z.number().min(0).max(10),
});
/** TypeScript type for safety category. */
export type SafetyCategory = z.infer<typeof safetyCategorySchema>;

/** Zod schema for travel advisory safety result. */
export const safetyResultSchema = z.object({
  categories: z.array(safetyCategorySchema),
  destination: z.string().min(1),
  lastUpdated: z.string().optional(),
  overallScore: z.number().min(0).max(10),
  provider: z.string().min(1),
  sourceUrl: z.url().optional(),
  summary: z.string().optional(),
});
/** TypeScript type for safety result. */
export type SafetyResult = z.infer<typeof safetyResultSchema>;

/** Zod schema for tool execution user context. */
export const userContextSchema = z.object({
  ip: z.string().optional(),
  sessionId: z.string().optional(),
  userId: z.string().min(1),
});
/** TypeScript type for user context. */
export type UserContext = z.infer<typeof userContextSchema>;

/** Zod schema for tool execution dependencies. */
export const executionDepsSchema = z.object({
  now: z.function().optional(), // Function returning number (not serializable)
  redis: z.unknown().optional(), // Redis client (not serializable)
});
/** TypeScript type for execution dependencies. */
export type ExecutionDeps = z.infer<typeof executionDepsSchema>;

/** Zod schema for approval context. */
export const approvalContextSchema = z.object({
  requireApproval: z.function().optional(), // Function (not serializable)
});
/** TypeScript type for approval context. */
export type ApprovalContext = z.infer<typeof approvalContextSchema>;

/** Zod schema for tool execution context (combines user, deps, and approval). */
export const toolExecutionContextSchema = userContextSchema
  .merge(executionDepsSchema)
  .merge(approvalContextSchema);
/** TypeScript type for tool execution context. */
export type ToolExecutionContext = z.infer<typeof toolExecutionContextSchema>;

/** Zod schema for rate limit result. */
export const rateLimitResultSchema = z.object({
  limit: z.number().int().nonnegative().optional(),
  remaining: z.number().int().nonnegative().optional(),
  reset: z.number().int().nonnegative().optional(),
  success: z.boolean(),
});
/** TypeScript type for rate limit result. */
export type RateLimitResult = z.infer<typeof rateLimitResultSchema>;

/** Zod schema for tool error codes (matches TOOL_ERROR_CODES constant). */
export const toolErrorCodeSchema = z.enum([
  "accom_booking_failed",
  "accom_booking_session_required",
  "accom_availability_failed",
  "accom_availability_not_found",
  "accom_availability_rate_limited",
  "accom_availability_unauthorized",
  "accom_details_failed",
  "accom_details_not_configured",
  "accom_details_not_found",
  "accom_details_rate_limited",
  "accom_details_timeout",
  "accom_details_unauthorized",
  "accom_search_failed",
  "accom_search_not_configured",
  "accom_search_payment_required",
  "accom_search_rate_limited",
  "accom_search_timeout",
  "accom_search_unauthorized",
  "approval_backend_unavailable",
  "approval_missing_session",
  "approval_required",
  "invalid_params",
  "tool_execution_failed",
  "tool_rate_limited",
  "web_search_error",
  "web_search_failed",
  "web_search_not_configured",
  "web_search_payment_required",
  "web_search_rate_limited",
  "web_search_unauthorized",
]);
/** TypeScript type for tool error codes. */
export type ToolErrorCode = z.infer<typeof toolErrorCodeSchema>;

/** Zod schema for tool error details. */
export const toolErrorSchema = z.object({
  code: toolErrorCodeSchema,
  message: z.string().min(1),
  meta: z.record(z.string(), z.unknown()).optional(),
  name: z.literal("ToolError").optional(),
  stack: z.string().optional(),
});
/** TypeScript type for tool error (extends Error at runtime). */
export type ToolError = z.infer<typeof toolErrorSchema> & Error;

/** Zod schema for approval status. */
export const approvalStatusSchema = z.enum([
  "pending",
  "approved",
  "denied",
  "expired",
  "not_found",
]);
/** TypeScript type for approval status. */
export type ApprovalStatus = z.infer<typeof approvalStatusSchema>;
