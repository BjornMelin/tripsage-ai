/**
 * @fileoverview Chat session detail API route handlers.
 *
 * Methods: GET (get session if owned), DELETE (delete session owner only).
 */

import "server-only";

import type { NextRequest } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { deleteSession, getSession } from "../_handlers";

export const dynamic = "force-dynamic";

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
  })(async (_req, { supabase }) => {
    const { id } = await context.params;
    return getSession({ supabase }, id);
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
  })(async (_req, { supabase }) => {
    const { id } = await context.params;
    return deleteSession({ supabase }, id);
  })(req, context);
}
