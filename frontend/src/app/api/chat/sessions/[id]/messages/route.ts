/**
 * @fileoverview Chat session messages API route handlers.
 *
 * Methods: GET (list messages), POST (create message).
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { createMessage, listMessages } from "../../_handlers";

export const dynamic = "force-dynamic";

/**
 * Retrieves all messages for a specific chat session.
 *
 * @param req NextRequest object.
 * @param context Route context containing the session ID parameter.
 * @returns Promise resolving to Response with array of messages.
 */
export async function GET(
  req: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  return withApiGuards({
    auth: true,
    rateLimit: "chat:sessions:messages:list",
    telemetry: "chat.sessions.messages.list",
  })(async (_req, { supabase }) => {
    const { id: sessionId } = await context.params;
    return listMessages({ supabase }, sessionId);
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
export async function POST(
  req: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  return withApiGuards({
    auth: true,
    rateLimit: "chat:sessions:messages:create",
    telemetry: "chat.sessions.messages.create",
  })(async (request, { supabase }) => {
    const { id: sessionId } = await context.params;
    let body: { content: string; role?: string };
    try {
      body = await request.json();
    } catch {
      return NextResponse.json({ error: "bad_request" }, { status: 400 });
    }
    return createMessage({ supabase }, sessionId, body);
  })(req, context);
}
