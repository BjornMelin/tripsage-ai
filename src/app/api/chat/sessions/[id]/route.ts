/**
 * @fileoverview Chat session detail API route handlers.
 */

import "server-only";

// Security: Route handlers are dynamic by default with Cache Components.
// Using withApiGuards({ auth: true }) ensures this route uses cookies/headers,
// making it dynamic and preventing caching of user-specific data.

import type { NextRequest } from "next/server";
import type { RouteParamsContext } from "@/lib/api/factory";
import { withApiGuards } from "@/lib/api/factory";
import { parseStringId, requireUserId } from "@/lib/api/route-helpers";
import { createServerLogger } from "@/lib/telemetry/logger";
import { deleteSession, getSession } from "../_handlers";

/**
 * Retrieves a specific chat session if owned by the authenticated user.
 *
 * @param req NextRequest object.
 * @param context Route context containing the session ID parameter.
 * @returns Promise resolving to Response with session data or error.
 */
export function GET(
  req: NextRequest,
  context: { params: Promise<{ id: string }> }
): Promise<Response> {
  return withApiGuards({
    auth: true,
    botId: true,
    rateLimit: "chat:sessions:get",
    telemetry: "chat.sessions.get",
  })(async (_req, { supabase, user }, _data, routeContext: RouteParamsContext) => {
    const logger = createServerLogger("chat.sessions.get");
    const result = requireUserId(user);
    if (!result.ok) return result.error;
    const userId = result.data;
    const idResult = await parseStringId(routeContext, "id");
    if (!idResult.ok) return idResult.error;
    return getSession({ logger, supabase, userId }, idResult.data);
  })(req, context);
}

/**
 * Deletes a specific chat session if owned by the authenticated user.
 *
 * @param req NextRequest object.
 * @param context Route context containing the session ID parameter.
 * @returns Promise resolving to Response with no content or error.
 */
export function DELETE(
  req: NextRequest,
  context: { params: Promise<{ id: string }> }
): Promise<Response> {
  return withApiGuards({
    auth: true,
    botId: true,
    rateLimit: "chat:sessions:delete",
    telemetry: "chat.sessions.delete",
  })(async (_req, { supabase, user }, _data, routeContext: RouteParamsContext) => {
    const logger = createServerLogger("chat.sessions.delete");
    const result = requireUserId(user);
    if (!result.ok) return result.error;
    const userId = result.data;
    const idResult = await parseStringId(routeContext, "id");
    if (!idResult.ok) return idResult.error;
    return deleteSession({ logger, supabase, userId }, idResult.data);
  })(req, context);
}
