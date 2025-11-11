/**
 * @fileoverview Shared types and helpers for AI SDK v6 tool execution.
 */

import type { Redis } from "@upstash/redis";

export type UserContext = {
  userId: string;
  sessionId?: string;
  ip?: string;
};

export type ExecutionDeps = {
  redis?: Redis;
  now?: () => number;
};

export type ApprovalContext = {
  /** Marks a tool action as requiring explicit user approval. */
  requireApproval: (action: string, ctx: UserContext) => Promise<void>;
};

export type ToolExecutionContext = UserContext & ExecutionDeps & ApprovalContext;

// Using the return type of the `tool` helper is sufficient in practice,
// but we keep the registry typed as Record<string, unknown> to avoid
// tight coupling to internal AI SDK types.
export type AiTool = unknown;

export type RateLimitResult = {
  success: boolean;
  limit?: number;
  remaining?: number;
  reset?: number;
};
