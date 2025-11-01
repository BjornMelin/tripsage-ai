/**
 * @fileoverview BYOK delete route. Removes a user API key from Supabase Vault.
 * Route: DELETE /api/keys/[service]
 */
"use cache: private";

import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { buildRateLimitKey } from "@/lib/next/route-helpers";
import { deleteUserApiKey } from "@/lib/supabase/rpc";
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
 * Handle DELETE /api/keys/[service] to remove a user's provider API key.
 *
 * @param req Next.js request.
 * @param ctx Route params including the service identifier.
 * @returns 204 No Content on success; 400/401/429/500 on error.
 */
export async function DELETE(req: NextRequest, ctx: { params: { service: string } }) {
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

    const service = ctx.params?.service;
    if (!service || typeof service !== "string") {
      return NextResponse.json(
        { error: "Invalid service", code: "BAD_REQUEST" },
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

    await deleteUserApiKey(user.id, normalizedService);
    return new NextResponse(null, { status: 204 });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("/api/keys/[service] DELETE error:", {
      message,
      service: ctx.params?.service,
    });
    return NextResponse.json(
      { error: "Internal server error", code: "INTERNAL_ERROR" },
      { status: 500 }
    );
  }
}
