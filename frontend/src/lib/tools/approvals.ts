/**
 * @fileoverview Minimal approval flow utilities backed by Upstash Redis.
 * Server-only: do not import from client components.
 */
import { getRedis } from "@/lib/redis";
import type { ToolExecutionContext } from "./types";

const KEY = (sessionId: string, action: string) => `approve:${sessionId}:${action}`;

/**
 * Require approval for a sensitive action. Throws if not yet approved.
 */
export async function requireApproval(
  action: string,
  ctx: Pick<ToolExecutionContext, "sessionId">
): Promise<void> {
  if (!ctx.sessionId) throw new Error("approval_missing_session");
  const redis = getRedis();
  if (!redis) throw new Error("approval_backend_unavailable");
  const k = KEY(ctx.sessionId, action);
  const approved = await redis.get<string>(k);
  if (approved !== "yes") {
    // Mark as pending for the UI to surface.
    await redis.set(k, "pending", { ex: 300 });
    const err: Error & { meta?: { action: string; sessionId: string } } = new Error(
      "approval_required"
    );
    // Attach metadata for the UI handler to render a dialog.
    err.meta = { action, sessionId: ctx.sessionId };
    throw err;
  }
}

/**
 * Grant approval for a given action in the current session.
 */
export async function grantApproval(sessionId: string, action: string): Promise<void> {
  const redis = getRedis();
  if (!redis) throw new Error("approval_backend_unavailable");
  await redis.set(KEY(sessionId, action), "yes", { ex: 300 });
}
