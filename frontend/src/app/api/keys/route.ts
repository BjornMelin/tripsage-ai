/**
 * @fileoverview BYOK upsert route. Stores user-provided API keys in Supabase Vault via RPC.
 * Route: POST /api/keys
 */
"use cache";

import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { buildRateLimitKey } from "@/lib/next/route-helpers";
import { insertUserApiKey } from "@/lib/supabase/rpc";
import { createServerSupabase } from "@/lib/supabase/server";
import { getKeys, postKey } from "./_handlers";

/**
 * Set of allowed API service providers for key storage.
 */
const ALLOWED_SERVICES = new Set(["openai", "openrouter", "anthropic", "xai"]);

/**
 * Prefix for rate limit keys in Redis.
 */
const RATELIMIT_PREFIX = "ratelimit:keys";

/**
 * Builds a rate limiter instance if Redis environment variables are configured.
 *
 * @returns Ratelimit instance or undefined if Redis is not configured.
 */
function buildRateLimiter(): InstanceType<typeof Ratelimit> | undefined {
  const url = process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN;
  if (!url || !token) return undefined;
  return new Ratelimit({
    redis: Redis.fromEnv(),
    limiter: Ratelimit.slidingWindow(10, "1 m"),
    analytics: true,
    prefix: RATELIMIT_PREFIX,
  });
}

/**
 * Handle POST /api/keys to insert or replace a user's provider API key.
 *
 * @param req Next.js request containing JSON body with { service, api_key }.
 * @returns 204 No Content on success; 400/401/429/500 on error.
 */
export async function POST(req: NextRequest) {
  try {
    const ratelimitInstance = buildRateLimiter();
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

    let service: string | undefined;
    let api_key: string | undefined;
    try {
      const body = await req.json();
      service = body.service;
      api_key = body.api_key;
    } catch (parseError) {
      const message =
        parseError instanceof Error ? parseError.message : "Unknown JSON parse error";
      console.error("/api/keys POST JSON parse error:", { message });
      return NextResponse.json(
        { error: "Malformed JSON in request body", code: "BAD_REQUEST" },
        { status: 400 }
      );
    }

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

    const supabase = await createServerSupabase();
    return postKey(
      { supabase, insertUserApiKey: (u, s, k) => insertUserApiKey(u, s, k) },
      { service, api_key }
    );
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
    return getKeys({ supabase });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("/api/keys GET error:", { message });
    return NextResponse.json(
      { error: "Internal server error", code: "INTERNAL_ERROR" },
      { status: 500 }
    );
  }
}
