/**
 * @fileoverview Chat session messages API route handlers.
 *
 * Methods: GET (list messages), POST (create message).
 */

import "server-only";

// Security: Route handlers are dynamic by default with Cache Components.
// Using withApiGuards({ auth: true }) ensures this route uses cookies/headers,
// making it dynamic and preventing caching of user-specific data.

import type { NextRequest } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, requireUserId } from "@/lib/api/route-helpers";
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
  })(async (_req, { supabase, user }) => {
    const result = requireUserId(user);
    if ("error" in result) return result.error;
    const { userId } = result;
    const { id: sessionId } = await context.params;
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
  })(async (request, { supabase, user }) => {
    const result = requireUserId(user);
    if ("error" in result) return result.error;
    const { userId } = result;
    const { id: sessionId } = await context.params;
    let body: { content: string; role?: string };
    try {
      body = await request.json();
    } catch {
      return errorResponse({
        error: "bad_request",
        reason: "Malformed JSON in request body",
        status: 400,
      });
    }
    return createMessage({ supabase, userId }, sessionId, body);
  })(req, context);
}
