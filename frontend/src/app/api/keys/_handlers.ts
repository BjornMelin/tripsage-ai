/**
 * @fileoverview DI handlers for BYOK key routes (POST/GET).
 *
 * These handlers encapsulate the business logic for API key storage and
 * retrieval. The Next.js route adapters handle SSR-only concerns and pass in
 * typed dependencies.
 *
 * All handlers accept `userId` as a parameter since the route adapter already
 * guarantees authentication via `withApiGuards({ auth: true })`.
 */

import type { PostKeyBody } from "@schemas/api";
import { NextResponse } from "next/server";
import { errorResponse } from "@/lib/api/route-helpers";
import type { TypedServerSupabase } from "@/lib/supabase/server";

/** Set of allowed API service providers for key storage. */
const ALLOWED = new Set(["openai", "openrouter", "anthropic", "xai", "gateway"]);

/**
 * Dependencies interface for keys handlers.
 */
export interface KeysDeps {
  supabase: TypedServerSupabase;
  userId: string;
  insertUserApiKey: (userId: string, service: string, apiKey: string) => Promise<void>;
  upsertUserGatewayBaseUrl?: (userId: string, baseUrl: string) => Promise<void>;
}

/**
 * Insert or replace a user's provider API key.
 *
 * Expects a validated body from postKeyBodySchema. Service normalization and
 * validation are performed here before calling the RPC.
 *
 * @param deps Collaborators with a typed Supabase client, authenticated userId, and RPC inserter.
 * @param body Validated payload containing service and apiKey.
 * @returns 204 on success; otherwise a JSON error Response.
 */
export async function postKey(deps: KeysDeps, body: PostKeyBody): Promise<Response> {
  // Normalize service names once so every adapter and RPC sees the canonical lowercase id.
  const normalized = body.service.toLowerCase();
  if (!ALLOWED.has(normalized)) {
    return errorResponse({
      error: "bad_request",
      reason: "Unsupported service",
      status: 400,
    });
  }

  // If service is gateway and baseUrl provided, persist base URL metadata
  if (normalized === "gateway" && body.baseUrl && deps.upsertUserGatewayBaseUrl) {
    try {
      await deps.upsertUserGatewayBaseUrl(deps.userId, body.baseUrl);
    } catch (err) {
      return errorResponse({
        err,
        error: "db_error",
        reason: "Failed to persist gateway base URL",
        status: 500,
      });
    }
  }
  try {
    await deps.insertUserApiKey(deps.userId, normalized, body.apiKey);
  } catch (err) {
    return errorResponse({
      err,
      error: "db_error",
      reason: "Failed to store API key",
      status: 500,
    });
  }
  return new Response(null, { status: 204 });
}

/**
 * List key metadata for the authenticated user.
 *
 * @param deps Collaborators with a typed Supabase client and authenticated userId.
 * @returns List of key summaries or an error Response.
 */
export async function getKeys(deps: {
  supabase: TypedServerSupabase;
  userId: string;
}): Promise<Response> {
  const { data, error } = await deps.supabase
    .from("api_keys")
    .select("service, created_at, last_used")
    .eq("user_id", deps.userId)
    .order("service", { ascending: true });
  if (error) {
    return errorResponse({
      err: error,
      error: "db_error",
      reason: "Failed to fetch keys",
      status: 500,
    });
  }
  type ApiKeyRow = {
    // biome-ignore lint/style/useNamingConvention: mirrors DB columns
    created_at: string | null;
    // biome-ignore lint/style/useNamingConvention: mirrors DB columns
    last_used: string | null;
    service: string;
  };
  const rows: ApiKeyRow[] = (data ?? []) as ApiKeyRow[];
  const payload = rows.map((r) => ({
    createdAt: r.created_at ? String(r.created_at) : null,
    hasKey: true,
    isValid: true,
    lastUsed: r.last_used ?? null,
    service: String(r.service),
  }));
  return NextResponse.json(payload, { status: 200 });
}
