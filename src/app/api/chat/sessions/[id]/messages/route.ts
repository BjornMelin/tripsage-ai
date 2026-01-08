/**
 * @fileoverview Chat session messages API route handlers.
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
import { createServerLogger } from "@/lib/telemetry/logger";
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
    const logger = createServerLogger("chat.sessions.messages.list");
    const result = requireUserId(user);
    if (!result.ok) return result.error;
    const userId = result.data;
    const idResult = await parseStringId(routeContext, "id");
    if (!idResult.ok) return idResult.error;
    const sessionId = idResult.data;
    return listMessages({ logger, supabase, userId }, sessionId);
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
    const logger = createServerLogger("chat.sessions.messages.create");
    const result = requireUserId(user);
    if (!result.ok) return result.error;
    const userId = result.data;
    const idResult = await parseStringId(routeContext, "id");
    if (!idResult.ok) return idResult.error;
    const sessionId = idResult.data;
    const bodyResult = await parseJsonBody(request);
    if (!bodyResult.ok) return bodyResult.error;
    const validation = validateSchema(createMessageRequestSchema, bodyResult.data);
    if (!validation.ok) return validation.error;
    const validatedBody = validation.data;
    // Transform validated content to parts format expected by handler
    return createMessage({ logger, supabase, userId }, sessionId, {
      parts: [{ text: validatedBody.content, type: "text" }],
      role: validatedBody.role,
    });
  })(req, context);
}
