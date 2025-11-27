/**
 * @fileoverview Chat session messages API route handlers.
 *
 * Methods: GET (list messages), POST (create message).
 */

import "server-only";

// Security: Route handlers are dynamic by default with Cache Components.
// Using withApiGuards({ auth: true }) ensures this route uses cookies/headers,
// making it dynamic and preventing caching of user-specific data.

import { createMessageRequestSchema } from "@schemas/chat";
import type { NextRequest } from "next/server";
import type { RouteParamsContext } from "@/lib/api/factory";
import { withApiGuards } from "@/lib/api/factory";
import {
  parseJsonBody,
  parseStringId,
  requireUserId,
  validateSchema,
} from "@/lib/api/route-helpers";
import { createMessage, listMessages } from "../../_handlers";

/**
 * Retrieves all messages for a specific chat session.
 *
 * @param req NextRequest object.
 * @param context Route context containing the session ID parameter.
 * @returns Promise resolving to Response with array of messages.
 */
export function GET(req: NextRequest, context: { params: Promise<{ id: string }> }) {
  return withApiGuards({
    auth: true,
    rateLimit: "chat:sessions:messages:list",
    telemetry: "chat.sessions.messages.list",
  })(async (_req, { supabase, user }, _data, routeContext: RouteParamsContext) => {
    const result = requireUserId(user);
    if ("error" in result) return result.error;
    const { userId } = result;
    const idResult = await parseStringId(routeContext, "id");
    if ("error" in idResult) return idResult.error;
    const { id: sessionId } = idResult;
    return listMessages({ supabase, userId }, sessionId);
  })(req, context);
}

/**
 * Creates a new message in a specific chat session.
 *
 * Request body must contain message data.
 *
 * @param req NextRequest containing message data in body.
 * @param context Route context containing the session ID parameter.
 * @returns Promise resolving to Response with no content on success.
 */
export function POST(req: NextRequest, context: { params: Promise<{ id: string }> }) {
  return withApiGuards({
    auth: true,
    rateLimit: "chat:sessions:messages:create",
    telemetry: "chat.sessions.messages.create",
  })(async (request, { supabase, user }, _data, routeContext: RouteParamsContext) => {
    const result = requireUserId(user);
    if ("error" in result) return result.error;
    const { userId } = result;
    const idResult = await parseStringId(routeContext, "id");
    if ("error" in idResult) return idResult.error;
    const { id: sessionId } = idResult;
    const bodyResult = await parseJsonBody(request);
    if ("error" in bodyResult) return bodyResult.error;
    const validation = validateSchema(createMessageRequestSchema, bodyResult.body);
    if ("error" in validation) return validation.error;
    const validatedBody = validation.data;
    // Transform validated content to parts format expected by handler
    return createMessage({ supabase, userId }, sessionId, {
      parts: [{ text: validatedBody.content, type: "text" }],
      role: validatedBody.role,
    });
  })(req, context);
}
