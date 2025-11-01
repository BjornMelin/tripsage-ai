/**
 * @fileoverview BYOK upsert route. Stores user-provided API keys in Supabase Vault via RPC.
 * Route: POST /api/keys
 */
"use cache: private";

import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { buildRateLimitKey } from "@/lib/next/route-helpers";
import { insertUserApiKey } from "@/lib/supabase/rpc";
import { createServerSupabase } from "@/lib/supabase/server";

const ALLOWED_SERVICES = new Set(["openai", "openrouter", "anthropic", "xai"]);

const UPSTASH_URL = process.env.UPSTASH_REDIS_REST_URL;
const UPSTASH_TOKEN = process.env.UPSTASH_REDIS_REST_TOKEN;
const RATELIMIT_PREFIX = "ratelimit:keys";
const ratelimitInstance =
  UPSTASH_URL && UPSTASH_TOKEN
    ? new Ratelimit({
        redis: Redis.fromEnv(),
        limiter: Ratelimit.slidingWindow(10, "1 m"),
        analytics: true,
        prefix: RATELIMIT_PREFIX,
      })
    : undefined;

/**
 * Handle POST /api/keys to insert or replace a user's provider API key.
 *
 * @param req Next.js request containing JSON body with { service, api_key }.
 * @returns 204 No Content on success; 400/401/429/500 on error.
 */
export async function POST(req: NextRequest) {
  try {
    if (ratelimitInstance) {
      const identifier = buildRateLimitKey(req);
      const { success, limit, remaining, reset } =
        await ratelimitInstance.limit(identifier);
      if (!success) {
        return NextResponse.json(
          { error: "Rate limit exceeded", code: "RATE_LIMIT" },
          {
            status: 429,
            headers: {
              "X-RateLimit-Limit": String(limit),
              "X-RateLimit-Remaining": String(remaining),
              "X-RateLimit-Reset": String(reset),
            },
          }
        );
      }
    }

    const { service, api_key }: { service?: string; api_key?: string } = await req
      .json()
      .catch(() => ({}));

    if (
      !service ||
      !api_key ||
      typeof service !== "string" ||
      typeof api_key !== "string"
    ) {
      return NextResponse.json(
        { error: "Invalid request body", code: "BAD_REQUEST" },
        { status: 400 }
      );
    }

    const normalizedService = service.trim().toLowerCase();
    if (!ALLOWED_SERVICES.has(normalizedService)) {
      return NextResponse.json(
        { error: "Unsupported service", code: "BAD_REQUEST" },
        { status: 400 }
      );
    }

    // Validate authenticated user from SSR cookies
    const supabase = await createServerSupabase();
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Store key via SECURITY DEFINER RPC (admin client inside helper)
    await insertUserApiKey(user.id, normalizedService, api_key);

    return new NextResponse(null, { status: 204 });
  } catch (err) {
    // Redact potential secrets from logs
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("/api/keys POST error:", { message });
    return NextResponse.json(
      { error: "Internal server error", code: "INTERNAL_ERROR" },
      { status: 500 }
    );
  }
}

/**
 * Return metadata for the authenticated user's stored API keys.
 *
 * This endpoint returns only non-secret fields: service, created_at, last_used.
 *
 * @returns 200 with a list of key summaries; 401/500 on error.
 */
export async function GET() {
  try {
    const supabase = await createServerSupabase();
    const { data: auth } = await supabase.auth.getUser();
    if (!auth.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    const { data, error } = await supabase
      .from("api_keys")
      .select("service, created_at, last_used")
      .order("service", { ascending: true });
    if (error) {
      return NextResponse.json(
        { error: "Failed to fetch keys", code: "DB_ERROR" },
        { status: 500 }
      );
    }
    const rows =
      (data as Array<{
        service: unknown;
        created_at: unknown;
        last_used: unknown;
      }> | null) ?? [];
    const payload = rows.map((r) => ({
      service: String((r as any).service),
      created_at: String((r as any).created_at),
      last_used: (r as any).last_used ?? null,
      has_key: true,
      is_valid: true,
    }));
    return NextResponse.json(payload, { status: 200 });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("/api/keys GET error:", { message });
    return NextResponse.json(
      { error: "Internal server error", code: "INTERNAL_ERROR" },
      { status: 500 }
    );
  }
}
