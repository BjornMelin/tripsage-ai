/**
 * @fileoverview Shared types and helpers for AI SDK v6 tool execution.
 */

import type {
  ApprovalContext,
  ExecutionDeps,
  RateLimitResult,
  ToolExecutionContext,
  UserContext,
} from "@ai/tools/schemas/tools";

// Re-export types from schemas
export type {
  ApprovalContext,
  ExecutionDeps,
  RateLimitResult,
  ToolExecutionContext,
  UserContext,
};

// Keep registry as Record<string, unknown> to avoid AI SDK coupling.
export type AiTool = unknown;
