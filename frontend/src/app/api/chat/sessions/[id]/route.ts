/**
 * @fileoverview Chat session detail API route handlers.
 *
 * Methods: GET (get session if owned), DELETE (delete session owner only).
 */

import "server-only";

// Security: Route handlers are dynamic by default with Cache Components.
// Using withApiGuards({ auth: true }) ensures this route uses cookies/headers,
// making it dynamic and preventing caching of user-specific data.

import type { NextRequest } from "next/server";
import type { RouteParamsContext } from "@/lib/api/factory";
import { withApiGuards } from "@/lib/api/factory";
import { parseStringId, requireUserId } from "@/lib/api/route-helpers";
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
    rateLimit: "chat:sessions:get",
    telemetry: "chat.sessions.get",
  })(async (_req, { supabase, user }, _data, routeContext: RouteParamsContext) => {
    const result = requireUserId(user);
    if ("error" in result) return result.error;
    const { userId } = result;
    const idResult = await parseStringId(routeContext, "id");
    if ("error" in idResult) return idResult.error;
    const { id } = idResult;
    return getSession({ supabase, userId }, id);
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
    rateLimit: "chat:sessions:delete",
    telemetry: "chat.sessions.delete",
  })(async (_req, { supabase, user }, _data, routeContext: RouteParamsContext) => {
    const result = requireUserId(user);
    if ("error" in result) return result.error;
    const { userId } = result;
    const idResult = await parseStringId(routeContext, "id");
    if ("error" in idResult) return idResult.error;
    const { id } = idResult;
    return deleteSession({ supabase, userId }, id);
  })(req, context);
}
