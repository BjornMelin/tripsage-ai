/**
 * @fileoverview DI handlers for BYOK key routes (POST/GET).
 *
 * These handlers encapsulate the business logic for API key storage and
 * retrieval. The Next.js route adapters handle SSR-only concerns and pass in
 * typed dependencies.
 */
import type { SupabaseClient } from "@supabase/supabase-js";

/** Set of allowed API service providers for key storage. */
const ALLOWED = new Set(["openai", "openrouter", "anthropic", "xai"]);

/**
 * Dependencies interface for keys handlers.
 */
export interface KeysDeps {
  supabase: SupabaseClient<any>;
  insertUserApiKey: (userId: string, service: string, apiKey: string) => Promise<void>;
}

/**
 * Interface for the request body when posting an API key.
 */
export interface PostKeyBody {
  service?: string;
  api_key?: string;
}

/**
 * Insert or replace a user's provider API key.
 *
 * @param deps Collaborators with a typed Supabase client and RPC inserter.
 * @param body Payload containing service and api_key.
 * @returns 204 on success; otherwise a JSON error Response.
 */
export async function postKey(deps: KeysDeps, body: PostKeyBody): Promise<Response> {
  const service = body?.service;
  const apiKey = body?.api_key;
  if (
    !service ||
    !apiKey ||
    typeof service !== "string" ||
    typeof apiKey !== "string"
  ) {
    return new Response(
      JSON.stringify({ error: "Invalid request body", code: "BAD_REQUEST" }),
      {
        status: 400,
        headers: { "content-type": "application/json" },
      }
    );
  }
  const normalized = service.trim().toLowerCase();
  if (!ALLOWED.has(normalized)) {
    return new Response(
      JSON.stringify({ error: "Unsupported service", code: "BAD_REQUEST" }),
      {
        status: 400,
        headers: { "content-type": "application/json" },
      }
    );
  }

  const { data: auth } = await deps.supabase.auth.getUser();
  const user = auth?.user ?? null;
  if (!user) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: { "content-type": "application/json" },
    });
  }

  await deps.insertUserApiKey(user.id, normalized, apiKey);
  return new Response(null, { status: 204 });
}

/**
 * List key metadata for the authenticated user.
 *
 * @param deps Collaborators with a typed Supabase client.
 * @returns List of key summaries or an error Response.
 */
export async function getKeys(deps: {
  supabase: SupabaseClient<any>;
}): Promise<Response> {
  const { data: auth } = await deps.supabase.auth.getUser();
  const user = auth?.user ?? null;
  if (!user) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: { "content-type": "application/json" },
    });
  }
  const { data, error } = await deps.supabase
    .from("api_keys")
    .select("service_name, created_at, last_used_at")
    .eq("user_id", user.id)
    .order("service_name", { ascending: true });
  if (error) {
    return new Response(
      JSON.stringify({ error: "Failed to fetch keys", code: "DB_ERROR" }),
      {
        status: 500,
        headers: { "content-type": "application/json" },
      }
    );
  }
  const rows = data ?? [];
  const payload = rows.map((r: any) => ({
    service: String(r.service_name),
    created_at: String(r.created_at),
    last_used: r.last_used_at ?? null,
    has_key: true,
    is_valid: true,
  }));
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}
