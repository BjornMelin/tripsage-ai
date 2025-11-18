/**
 * @fileoverview DI handlers for BYOK key routes (POST/GET).
 *
 * These handlers encapsulate the business logic for API key storage and
 * retrieval. The Next.js route adapters handle SSR-only concerns and pass in
 * typed dependencies.
 */

import type { PostKeyBody } from "@/lib/schemas/api";
import type { TypedServerSupabase } from "@/lib/supabase/server";

/** Set of allowed API service providers for key storage. */
const ALLOWED = new Set(["openai", "openrouter", "anthropic", "xai", "gateway"]);

/**
 * Dependencies interface for keys handlers.
 */
export interface KeysDeps {
  supabase: TypedServerSupabase;
  insertUserApiKey: (userId: string, service: string, apiKey: string) => Promise<void>;
  upsertUserGatewayBaseUrl?: (userId: string, baseUrl: string) => Promise<void>;
}

/**
 * Insert or replace a user's provider API key.
 *
 * Expects a validated body from postKeyBodySchema. Service normalization and
 * validation are performed here before calling the RPC.
 *
 * @param deps Collaborators with a typed Supabase client and RPC inserter.
 * @param body Validated payload containing service and apiKey.
 * @returns 204 on success; otherwise a JSON error Response.
 */
export async function postKey(deps: KeysDeps, body: PostKeyBody): Promise<Response> {
  // Normalize service names once so every adapter and RPC sees the canonical lowercase id.
  const normalized = body.service.toLowerCase();
  if (!ALLOWED.has(normalized)) {
    return new Response(
      JSON.stringify({ code: "BAD_REQUEST", error: "Unsupported service" }),
      {
        headers: { "content-type": "application/json" },
        status: 400,
      }
    );
  }

  const { data: auth } = await deps.supabase.auth.getUser();
  const user = auth?.user ?? null;
  if (!user) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      headers: { "content-type": "application/json" },
      status: 401,
    });
  }

  // If service is gateway and baseUrl provided, persist base URL metadata
  if (normalized === "gateway" && body.baseUrl && deps.upsertUserGatewayBaseUrl) {
    await deps.upsertUserGatewayBaseUrl(user.id, body.baseUrl);
  }
  await deps.insertUserApiKey(user.id, normalized, body.apiKey);
  return new Response(null, { status: 204 });
}

/**
 * List key metadata for the authenticated user.
 *
 * @param deps Collaborators with a typed Supabase client.
 * @returns List of key summaries or an error Response.
 */
export async function getKeys(deps: {
  supabase: TypedServerSupabase;
}): Promise<Response> {
  const { data: auth } = await deps.supabase.auth.getUser();
  const user = auth?.user ?? null;
  if (!user) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      headers: { "content-type": "application/json" },
      status: 401,
    });
  }
  const { data, error } = await deps.supabase
    .from("api_keys")
    // Align with table column names used across codebase/tests
    .select("service_name, created_at, last_used_at")
    .eq("user_id", user.id)
    .order("service_name", { ascending: true });
  if (error) {
    return new Response(
      JSON.stringify({ code: "DB_ERROR", error: "Failed to fetch keys" }),
      {
        headers: { "content-type": "application/json" },
        status: 500,
      }
    );
  }
  const rows = data ?? [];
  const payload = rows.map(
    (r: {
      // biome-ignore lint/style/useNamingConvention: DB field names
      service_name: string;
      // biome-ignore lint/style/useNamingConvention: DB field names
      created_at: string;
      // biome-ignore lint/style/useNamingConvention: DB field names
      last_used_at: string | null;
    }) => ({
      createdAt: String(r.created_at),
      hasKey: true,
      isValid: true,
      lastUsed: r.last_used_at ?? null,
      service: String(r.service_name),
    })
  );
  return new Response(JSON.stringify(payload), {
    headers: { "content-type": "application/json" },
    status: 200,
  });
}
