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
    const { data: auth } = await supabase.auth.getUser();
    const user = auth.user;
    if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

    const { id } = ctx.params;
    const { data, error } = await supabase
      .from("chat_sessions")
      .select("id, created_at, updated_at, metadata")
      .eq("id", id)
      .eq("user_id", user.id)
      .maybeSingle();
    if (error) return NextResponse.json({ error: "db_error" }, { status: 500 });
    if (!data) return NextResponse.json({ error: "not_found" }, { status: 404 });
    return NextResponse.json(data, { status: 200 });
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
    const { data: auth } = await supabase.auth.getUser();
    const user = auth.user;
    if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

    const { id } = ctx.params;
    const { error } = await supabase
      .from("chat_sessions")
      .delete()
      .eq("id", id)
      .eq("user_id", user.id);
    if (error) return NextResponse.json({ error: "db_error" }, { status: 500 });
    return new NextResponse(null, { status: 204 });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("/api/chat/sessions/[id] DELETE error", { message });
    return NextResponse.json({ error: "internal" }, { status: 500 });
  }
}
