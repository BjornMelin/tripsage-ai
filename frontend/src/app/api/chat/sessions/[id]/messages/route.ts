/**
 * @fileoverview Chat session messages API.
 * Routes:
 *  - GET  /api/chat/sessions/[id]/messages   -> list messages
 *  - POST /api/chat/sessions/[id]/messages   -> create message
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase";
import { createMessage, listMessages } from "../../_handlers";

export const dynamic = "force-dynamic";

/**
 * Retrieves all messages for a specific chat session.
 *
 * @param _req - The Next.js request object (unused).
 * @param ctx - Route context containing the session ID parameter.
 * @returns Promise resolving to a Response with array of messages.
 */
export async function GET(
  _req: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  try {
    const supabase = await createServerSupabase();
    const { id: sessionId } = await context.params;
    return listMessages({ supabase }, sessionId);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("/api/chat/sessions/[id]/messages GET error", { message });
    return NextResponse.json({ error: "internal" }, { status: 500 });
  }
}

/**
 * Creates a new message in a specific chat session.
 *
 * @param req - The Next.js request object containing message data.
 * @param ctx - Route context containing the session ID parameter.
 * @returns Promise resolving to a Response with no content on success.
 */
export async function POST(
  req: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  try {
    const supabase = await createServerSupabase();
    const { id: sessionId } = await context.params;
    let body: { content: string; role?: string };
    try {
      body = await req.json();
    } catch {
      return NextResponse.json({ error: "bad_request" }, { status: 400 });
    }
    return createMessage({ supabase }, sessionId, body);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("/api/chat/sessions/[id]/messages POST error", { message });
    return NextResponse.json({ error: "internal" }, { status: 500 });
  }
}
