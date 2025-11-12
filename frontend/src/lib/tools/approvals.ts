/**
 * @fileoverview Minimal approval flow utilities backed by Upstash Redis.
 * Server-only: do not import from client components.
 */

import { getRedis } from "@/lib/redis";
import type { ToolExecutionContext } from "./types";

const KEY = (sessionId: string, action: string, idempotencyKey?: string) =>
  idempotencyKey
    ? `approve:${sessionId}:${action}:${idempotencyKey}`
    : `approve:${sessionId}:${action}`;

export type ApprovalStatus =
  | "pending"
  | "approved"
  | "denied"
  | "expired"
  | "not_found";

/**
 * Require approval for a sensitive action. Throws if not yet approved.
 *
 * @param action - The action to require approval for.
 * @param ctx - The tool execution context.
 * @returns A promise that resolves when the action is approved.
 * @throws {Error} Error with `code` property set to "approval_required" if the action is not approved.
 */
export async function requireApproval(
  action: string,
  ctx: Pick<ToolExecutionContext, "sessionId"> & { idempotencyKey?: string }
): Promise<void> {
  if (!ctx.sessionId) throw new Error("approval_missing_session");
  const redis = getRedis();
  if (!redis) throw new Error("approval_backend_unavailable");
  const k = KEY(ctx.sessionId, action, ctx.idempotencyKey);
  const approved = await redis.get<string>(k);
  if (approved !== "yes") {
    // Mark as pending for the UI to surface.
    await redis.set(k, "pending", { ex: 300 });
    const err: Error & {
      code?: string;
      meta?: { action: string; sessionId: string; idempotencyKey?: string };
    } = new Error("approval_required");
    err.code = "approval_required";
    // Attach metadata for the UI handler to render a dialog.
    err.meta = {
      action,
      sessionId: ctx.sessionId,
      ...(ctx.idempotencyKey ? { idempotencyKey: ctx.idempotencyKey } : {}),
    };
    throw err;
  }
}

/**
 * Get approval status for a given action and optional idempotency key.
 *
 * @param sessionId - The session ID.
 * @param action - The action to get the approval status for.
 * @param idempotencyKey - The idempotency key.
 * @returns The approval status.
 */
export async function getApprovalStatus(
  sessionId: string,
  action: string,
  idempotencyKey?: string
): Promise<ApprovalStatus> {
  const redis = getRedis();
  if (!redis) return "expired";
  const k = KEY(sessionId, action, idempotencyKey);
  const status = await redis.get<string>(k);
  if (status === "yes") return "approved";
  if (status === "pending") return "pending";
  if (status === "denied") return "denied";
  return "not_found";
}

/**
 * Grant approval for a given action in the current session.
 *
 * @param sessionId - The session ID.
 * @param action - The action to grant approval for.
 * @param idempotencyKey - The idempotency key.
 */
export async function grantApproval(
  sessionId: string,
  action: string,
  idempotencyKey?: string
): Promise<void> {
  const redis = getRedis();
  if (!redis) throw new Error("approval_backend_unavailable");
  await redis.set(KEY(sessionId, action, idempotencyKey), "yes", { ex: 300 });
}

/**
 * Deny approval for a given action in the current session.
 *
 * @param sessionId - The session ID.
 * @param action - The action to deny approval for.
 * @param idempotencyKey - The idempotency key.
 */
export async function denyApproval(
  sessionId: string,
  action: string,
  idempotencyKey?: string
): Promise<void> {
  const redis = getRedis();
  if (!redis) throw new Error("approval_backend_unavailable");
  await redis.set(KEY(sessionId, action, idempotencyKey), "denied", { ex: 300 });
}
