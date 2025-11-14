/**
 * @fileoverview Chat sessions API.
 * Routes:
 *  - POST /api/chat/sessions    -> create session
 *  - GET  /api/chat/sessions    -> list sessions for current user
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase";
import { createSession, listSessions } from "./_handlers";

export const dynamic = "force-dynamic";

/**
 * Creates a new chat session for the authenticated user.
 *
 * @param req - The Next.js request object containing optional title in body.
 * @returns Promise resolving to a Response with the created session ID.
 */
export async function POST(req: NextRequest) {
  try {
    const supabase = await createServerSupabase();
    let title: string | undefined;
    try {
      const body = (await req.json()) as { title?: string };
      title = body?.title;
    } catch {
      // Intentionally ignore JSON parsing errors - title is optional
    }
    return createSession({ supabase }, title);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("/api/chat/sessions POST error", { message });
    return NextResponse.json({ error: "internal" }, { status: 500 });
  }
}

/**
 * Retrieves all chat sessions for the authenticated user.
 *
 * @returns Promise resolving to a Response with array of user's chat sessions.
 */
export async function GET() {
  try {
    const supabase = await createServerSupabase();
    return listSessions({ supabase });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("/api/chat/sessions GET error", { message });
    return NextResponse.json({ error: "internal" }, { status: 500 });
  }
}
