/**
 * @fileoverview DI handlers for chat sessions/messages routes.
 *
 * These handlers encapsulate CRUD operations for chat sessions and messages.
 * Adapters (route.ts files) provide SSR-only dependencies and translate the
 * HTTP details to simple POJOs used here.
 *
 * All handlers accept `userId` as a parameter since the route adapter already
 * guarantees authentication via `withApiGuards({ auth: true })`.
 */
import { NextResponse } from "next/server";
import { errorResponse, notFoundResponse } from "@/lib/api/route-helpers";
import { nowIso, secureUuid } from "@/lib/security/random";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { insertSingle } from "@/lib/supabase/typed-helpers";

/**
 * Dependencies interface for sessions handlers.
 */
export interface SessionsDeps {
  supabase: TypedServerSupabase;
  userId: string;
}

/**
 * Create a chat session owned by the authenticated user.
 * @param deps Collaborators with Supabase client and authenticated userId.
 * @param title Optional title (stored in metadata).
 */
export async function createSession(
  deps: SessionsDeps,
  title?: string
): Promise<Response> {
  const id = secureUuid();
  const now = nowIso();
  const { error } = await insertSingle(deps.supabase, "chat_sessions", {
    // biome-ignore lint/style/useNamingConvention: Database field name
    created_at: now,
    id,
    metadata: title ? { title } : {},
    // biome-ignore lint/style/useNamingConvention: Database field name
    updated_at: now,
    // biome-ignore lint/style/useNamingConvention: Database field name
    user_id: deps.userId,
  });
  if (error)
    return errorResponse({
      error: "db_error",
      reason: "Failed to create session",
      status: 500,
    });
  return NextResponse.json({ id }, { status: 201 });
}

/**
 * List sessions for the authenticated user.
 */
export async function listSessions(deps: SessionsDeps): Promise<Response> {
  const { data, error } = await deps.supabase
    .from("chat_sessions")
    .select("id, created_at, updated_at, metadata")
    .eq("user_id", deps.userId)
    .order("updated_at", { ascending: false });
  if (error)
    return errorResponse({
      error: "db_error",
      reason: "Failed to list sessions",
      status: 500,
    });
  return NextResponse.json(data ?? [], { status: 200 });
}

/**
 * Get a single session by id (owner-only).
 */
export async function getSession(deps: SessionsDeps, id: string): Promise<Response> {
  const { data, error } = await deps.supabase
    .from("chat_sessions")
    .select("id, created_at, updated_at, metadata")
    .eq("id", id)
    .eq("user_id", deps.userId)
    .maybeSingle();
  if (error)
    return errorResponse({
      error: "db_error",
      reason: "Failed to get session",
      status: 500,
    });
  if (!data) return notFoundResponse("Session");
  return NextResponse.json(data, { status: 200 });
}

/**
 * Delete a session by id (owner-only).
 */
export async function deleteSession(deps: SessionsDeps, id: string): Promise<Response> {
  const { error } = await deps.supabase
    .from("chat_sessions")
    .delete()
    .eq("id", id)
    .eq("user_id", deps.userId);
  if (error)
    return errorResponse({
      error: "db_error",
      reason: "Failed to delete session",
      status: 500,
    });
  return new Response(null, { status: 204 });
}

/**
 * List messages for a session.
 */
export async function listMessages(deps: SessionsDeps, id: string): Promise<Response> {
  const { data: session, error: sessionError } = await deps.supabase
    .from("chat_sessions")
    .select("id")
    .eq("id", id)
    .eq("user_id", deps.userId)
    .maybeSingle();
  if (sessionError)
    return errorResponse({
      error: "db_error",
      reason: "Failed to verify session",
      status: 500,
    });
  if (!session) return notFoundResponse("Session");
  const { data, error } = await deps.supabase
    .from("chat_messages")
    .select("id, role, content, created_at, metadata")
    .eq("session_id", id)
    .eq("user_id", deps.userId)
    .order("id", { ascending: true });
  if (error)
    return errorResponse({
      error: "db_error",
      reason: "Failed to list messages",
      status: 500,
    });
  return NextResponse.json(data ?? [], { status: 200 });
}

/**
 * Create a message within a session for the authenticated user.
 */
export async function createMessage(
  deps: SessionsDeps,
  id: string,
  payload: { role?: string; parts?: unknown[] }
): Promise<Response> {
  if (!payload?.role || typeof payload.role !== "string")
    return errorResponse({
      error: "bad_request",
      reason: "Role is required",
      status: 400,
    });
  const normalizedRole = payload.role.toLowerCase();
  if (!["user", "assistant", "system"].includes(normalizedRole)) {
    return errorResponse({
      error: "bad_request",
      reason: "Role must be user, assistant, or system",
      status: 400,
    });
  }
  const { data: session, error: sessionError } = await deps.supabase
    .from("chat_sessions")
    .select("id")
    .eq("id", id)
    .eq("user_id", deps.userId)
    .maybeSingle();
  if (sessionError)
    return errorResponse({
      error: "db_error",
      reason: "Failed to verify session",
      status: 500,
    });
  if (!session) return notFoundResponse("Session");
  const content = JSON.stringify(payload.parts ?? []);
  const { error } = await insertSingle(deps.supabase, "chat_messages", {
    content,
    metadata: {},
    role: normalizedRole as "user" | "system" | "assistant",
    // biome-ignore lint/style/useNamingConvention: Database field name
    session_id: id,
    // biome-ignore lint/style/useNamingConvention: Database field name
    user_id: deps.userId,
  });
  if (error)
    return errorResponse({
      error: "db_error",
      reason: "Failed to create message",
      status: 500,
    });
  return new Response(null, { status: 201 });
}
