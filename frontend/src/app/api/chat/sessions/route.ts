/**
 * @fileoverview Chat sessions API route handlers.
 *
 * Methods: POST (create session), GET (list sessions for current user).
 */

import "server-only";

// Security: Route handlers are dynamic by default with Cache Components.
// Using withApiGuards({ auth: true }) ensures this route uses cookies/headers,
// making it dynamic and preventing caching of user-specific data.

import type { NextRequest } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { parseJsonBody } from "@/lib/next/route-helpers";
import { createSession, listSessions } from "./_handlers";

/**
 * Creates a new chat session for the authenticated user.
 *
 * Request body may contain optional `title` field.
 *
 * @param req NextRequest containing optional title in body.
 * @returns Promise resolving to Response with created session ID.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "chat:sessions:create",
  telemetry: "chat.sessions.create",
})(async (req: NextRequest, { supabase }) => {
  // Title is optional, so gracefully handle parsing errors
  const parsed = await parseJsonBody(req);
  const title =
    "error" in parsed ? undefined : (parsed.body as { title?: string })?.title;
  return createSession({ supabase }, title);
});

/**
 * Retrieves all chat sessions for the authenticated user.
 *
 * @returns Promise resolving to Response with array of user's chat sessions.
 */
export const GET = withApiGuards({
  auth: true,
  rateLimit: "chat:sessions:list",
  telemetry: "chat.sessions.list",
})((_req, { supabase }) => {
  return listSessions({ supabase });
});
