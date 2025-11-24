/**
 * @fileoverview DI handlers for chat sessions/messages routes.
 *
 * These handlers encapsulate CRUD operations for chat sessions and messages.
 * Adapters (route.ts files) provide SSR-only dependencies and translate the
 * HTTP details to simple POJOs used here.
 */
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { insertSingle } from "@/lib/supabase/typed-helpers";

/**
 * Dependencies interface for sessions handlers.
 */
export interface SessionsDeps {
  supabase: TypedServerSupabase;
}

/**
 * Create a chat session owned by the authenticated user.
 * @param deps Collaborators with Supabase client.
 * @param title Optional title (stored in metadata).
 */
export async function createSession(
  deps: SessionsDeps,
  title?: string
): Promise<Response> {
  const { data: auth } = await deps.supabase.auth.getUser();
  const user = auth?.user ?? null;
  if (!user) return json({ error: "unauthorized" }, 401);
  const id = crypto.randomUUID?.() ?? Math.random().toString(36).slice(2);
  const now = new Date().toISOString();
  const { error } = await insertSingle(deps.supabase, "chat_sessions", {
    // biome-ignore lint/style/useNamingConvention: Database field name
    created_at: now,
    id,
    metadata: title ? { title } : {},
    // biome-ignore lint/style/useNamingConvention: Database field name
    updated_at: now,
    // biome-ignore lint/style/useNamingConvention: Database field name
    user_id: user.id,
  });
  if (error) return json({ error: "db_error" }, 500);
  return json({ id }, 201);
}

/**
 * List sessions for the authenticated user.
 */
export async function listSessions(deps: SessionsDeps): Promise<Response> {
  const { data: auth } = await deps.supabase.auth.getUser();
  const user = auth?.user ?? null;
  if (!user) return json({ error: "unauthorized" }, 401);
  const { data, error } = await deps.supabase
    .from("chat_sessions")
    .select("id, created_at, updated_at, metadata")
    .eq("user_id", user.id)
    .order("updated_at", { ascending: false });
  if (error) return json({ error: "db_error" }, 500);
  return json(data ?? [], 200);
}

/**
 * Get a single session by id (owner-only).
 */
export async function getSession(deps: SessionsDeps, id: string): Promise<Response> {
  const { data: auth } = await deps.supabase.auth.getUser();
  const user = auth?.user ?? null;
  if (!user) return json({ error: "unauthorized" }, 401);
  const { data, error } = await deps.supabase
    .from("chat_sessions")
    .select("id, created_at, updated_at, metadata")
    .eq("id", id)
    .eq("user_id", user.id)
    .maybeSingle();
  if (error) return json({ error: "db_error" }, 500);
  if (!data) return json({ error: "not_found" }, 404);
  return json(data, 200);
}

/**
 * Delete a session by id (owner-only).
 */
export async function deleteSession(deps: SessionsDeps, id: string): Promise<Response> {
  const { data: auth } = await deps.supabase.auth.getUser();
  const user = auth?.user ?? null;
  if (!user) return json({ error: "unauthorized" }, 401);
  const { error } = await deps.supabase
    .from("chat_sessions")
    .delete()
    .eq("id", id)
    .eq("user_id", user.id);
  if (error) return json({ error: "db_error" }, 500);
  return new Response(null, { status: 204 });
}

/**
 * List messages for a session.
 */
export async function listMessages(deps: SessionsDeps, id: string): Promise<Response> {
  const { data: auth } = await deps.supabase.auth.getUser();
  const user = auth?.user ?? null;
  if (!user) return json({ error: "unauthorized" }, 401);
  const { data: session, error: sessionError } = await deps.supabase
    .from("chat_sessions")
    .select("id")
    .eq("id", id)
    .eq("user_id", user.id)
    .maybeSingle();
  if (sessionError) return json({ error: "db_error" }, 500);
  if (!session) return json({ error: "not_found" }, 404);
  const { data, error } = await deps.supabase
    .from("chat_messages")
    .select("id, role, content, created_at, metadata")
    .eq("session_id", id)
    .eq("user_id", user.id)
    .order("id", { ascending: true });
  if (error) return json({ error: "db_error" }, 500);
  return json(data ?? [], 200);
}

/**
 * Create a message within a session for the authenticated user.
 */
export async function createMessage(
  deps: SessionsDeps,
  id: string,
  payload: { role?: string; parts?: unknown[] }
): Promise<Response> {
  const { data: auth } = await deps.supabase.auth.getUser();
  const user = auth?.user ?? null;
  if (!user) return json({ error: "unauthorized" }, 401);
  if (!payload?.role || typeof payload.role !== "string")
    return json({ error: "bad_request" }, 400);
  const normalizedRole = payload.role.toLowerCase();
  if (!["user", "assistant", "system"].includes(normalizedRole)) {
    return json({ error: "bad_request" }, 400);
  }
  const { data: session, error: sessionError } = await deps.supabase
    .from("chat_sessions")
    .select("id")
    .eq("id", id)
    .eq("user_id", user.id)
    .maybeSingle();
  if (sessionError) return json({ error: "db_error" }, 500);
  if (!session) return json({ error: "not_found" }, 404);
  const content = JSON.stringify(payload.parts ?? []);
  const { error } = await insertSingle(deps.supabase, "chat_messages", {
    content,
    metadata: {},
    role: normalizedRole as "user" | "system" | "assistant",
    // biome-ignore lint/style/useNamingConvention: Database field name
    session_id: id,
    // biome-ignore lint/style/useNamingConvention: Database field name
    user_id: user.id,
  });
  if (error) return json({ error: "db_error" }, 500);
  return new Response(null, { status: 201 });
}

/**
 * Creates a JSON Response with the specified status code.
 *
 * @param obj - Object to serialize as JSON.
 * @param status - HTTP status code for the response.
 * @returns Response with JSON content and appropriate headers.
 */
function json(obj: unknown, status: number): Response {
  return new Response(JSON.stringify(obj), {
    headers: { "content-type": "application/json" },
    status,
  });
}
