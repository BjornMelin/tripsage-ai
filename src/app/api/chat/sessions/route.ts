/**
 * @fileoverview Chat sessions API route handlers.
 */

import "server-only";

// Security: Route handlers are dynamic by default with Cache Components.
// Using withApiGuards({ auth: true }) ensures this route uses cookies/headers,
// making it dynamic and preventing caching of user-specific data.

import type { NextRequest } from "next/server";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, parseJsonBody, requireUserId } from "@/lib/api/route-helpers";
import { createServerLogger } from "@/lib/telemetry/logger";
import { createSession, listSessions } from "./_handlers";

const createSessionBodySchema = z.looseObject({
  title: z
    .string()
    .trim()
    .min(1, { error: "Title cannot be empty" })
    .max(200, {
      error: "Title too long",
    })
    .optional(),
});

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
  botId: true,
  rateLimit: "chat:sessions:create",
  telemetry: "chat.sessions.create",
})(async (req: NextRequest, { supabase, user }) => {
  const logger = createServerLogger("chat.sessions.create");
  const result = requireUserId(user);
  if (!result.ok) return result.error;
  const userId = result.data;
  // Title is optional, so gracefully handle parsing errors
  const parsed = await parseJsonBody(req);
  if (!parsed.ok) {
    // Preserve backwards-compat for "no body" requests, but fail hard on oversized payloads.
    if (parsed.error.status === 413) {
      return parsed.error;
    }
    return createSession({ logger, supabase, userId }, undefined);
  }

  const validation = createSessionBodySchema.safeParse(parsed.data);
  if (!validation.success) {
    return errorResponse({
      err: validation.error,
      error: "invalid_request",
      issues: validation.error.issues,
      reason: "Invalid request body",
      status: 400,
    });
  }

  const title = validation.data.title;
  return createSession({ logger, supabase, userId }, title);
});

/**
 * Retrieves all chat sessions for the authenticated user.
 *
 * @returns Promise resolving to Response with array of user's chat sessions.
 */
export const GET = withApiGuards({
  auth: true,
  botId: true,
  rateLimit: "chat:sessions:list",
  telemetry: "chat.sessions.list",
})((_req, { supabase, user }) => {
  const logger = createServerLogger("chat.sessions.list");
  const result = requireUserId(user);
  if (!result.ok) return result.error;
  const userId = result.data;
  return listSessions({ logger, supabase, userId });
});
