/**
 * @fileoverview Chat session detail API.
 * Routes:
 *  - GET    /api/chat/sessions/[id]    -> get session (if owned)
 *  - DELETE /api/chat/sessions/[id]    -> delete session (owner only)
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase/server";
import { deleteSession, getSession } from "../_handlers";

export const dynamic = "force-dynamic";

/**
 * Retrieves a specific chat session if owned by the authenticated user.
 *
 * @param _req - The Next.js request object (unused).
 * @param ctx - Route context containing the session ID parameter.
 * @returns Promise resolving to a Response with session data or error.
 */
export async function GET(_req: NextRequest, ctx: { params: { id: string } }) {
  try {
    const supabase = await createServerSupabase();
    const { id } = ctx.params;
    return getSession({ supabase }, id);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("/api/chat/sessions/[id] GET error", { message });
    return NextResponse.json({ error: "internal" }, { status: 500 });
  }
}

/**
 * Deletes a specific chat session if owned by the authenticated user.
 *
 * @param _req - The Next.js request object (unused).
 * @param ctx - Route context containing the session ID parameter.
 * @returns Promise resolving to a Response with no content or error.
 */
export async function DELETE(_req: NextRequest, ctx: { params: { id: string } }) {
  try {
    const supabase = await createServerSupabase();
    const { id } = ctx.params;
    return deleteSession({ supabase }, id);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("/api/chat/sessions/[id] DELETE error", { message });
    return NextResponse.json({ error: "internal" }, { status: 500 });
  }
}
