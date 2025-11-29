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
import type { Tool, ToolCallOptions } from "ai";

// Re-export types from schemas
export type {
  ApprovalContext,
  ExecutionDeps,
  RateLimitResult,
  ToolExecutionContext,
  UserContext,
};

/** Canonical AI tool contract used across registry-aware agents. */
export type AiTool = Tool<unknown, unknown>;
