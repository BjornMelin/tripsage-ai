/**
 * @fileoverview BYOK validate route. Checks if a provided API key is valid for a given service.
 * Route: POST /api/keys/validate
 * Never persists the key.
 */
"use cache: private";
export const dynamic = "force-dynamic";

import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { buildRateLimitKey } from "@/lib/next/route-helpers";
import { createServerSupabase } from "@/lib/supabase/server";

const UPSTASH_URL = process.env.UPSTASH_REDIS_REST_URL;
const UPSTASH_TOKEN = process.env.UPSTASH_REDIS_REST_TOKEN;
const RATELIMIT_PREFIX = "ratelimit:keys-validate";
const ratelimitInstance =
  UPSTASH_URL && UPSTASH_TOKEN
    ? new Ratelimit({
        redis: Redis.fromEnv(),
        limiter: Ratelimit.slidingWindow(20, "1 m"),
        analytics: true,
        prefix: RATELIMIT_PREFIX,
      })
    : undefined;

type ValidateResult = { is_valid: boolean; reason?: string };

/**
 * Validate a provider key by making a minimal metadata request.
 *
 * @param service Provider identifier (openai|openrouter|anthropic|xai).
 * @param apiKey The plaintext API key to check.
 * @returns Validation result with is_valid and optional reason.
 */
async function validateProviderKey(
  service: string,
  apiKey: string
): Promise<ValidateResult> {
  const svc = service.trim().toLowerCase();
  try {
    if (svc === "openai") {
      const res = await fetch("https://api.openai.com/v1/models", {
        method: "GET",
        headers: { Authorization: `Bearer ${apiKey}` },
      });
      if (res.status === 200) return { is_valid: true };
      if (res.status === 401 || res.status === 403)
        return { is_valid: false, reason: "Unauthorized" };
      return { is_valid: false, reason: `HTTP_${res.status}` };
    }
    if (svc === "openrouter") {
      const res = await fetch("https://openrouter.ai/api/v1/models", {
        method: "GET",
        headers: { Authorization: `Bearer ${apiKey}` },
      });
      if (res.status === 200) return { is_valid: true };
      if (res.status === 401 || res.status === 403)
        return { is_valid: false, reason: "Unauthorized" };
      return { is_valid: false, reason: `HTTP_${res.status}` };
    }
    if (svc === "anthropic") {
      const res = await fetch("https://api.anthropic.com/v1/models", {
        method: "GET",
        headers: { "x-api-key": apiKey, "anthropic-version": "2023-06-01" },
      });
      if (res.status === 200) return { is_valid: true };
      if (res.status === 401 || res.status === 403)
        return { is_valid: false, reason: "Unauthorized" };
      return { is_valid: false, reason: `HTTP_${res.status}` };
    }
    if (svc === "xai") {
      const res = await fetch("https://api.x.ai/v1/models", {
        method: "GET",
        headers: { Authorization: `Bearer ${apiKey}` },
      });
      if (res.status === 200) return { is_valid: true };
      if (res.status === 401 || res.status === 403)
        return { is_valid: false, reason: "Unauthorized" };
      return { is_valid: false, reason: `HTTP_${res.status}` };
    }
    return { is_valid: false, reason: "Invalid service" };
  } catch (_error) {
    return { is_valid: false, reason: "NETWORK_ERROR" };
  }
}

/**
 * Handle POST /api/keys/validate to verify a user-supplied API key.
 *
 * @param req Next.js request containing JSON body with { service, api_key }.
 * @returns 200 with validation result; 400/401/429/500 on error.
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

    // Require authenticated user to prevent anonymous credential probing
    const supabase = await createServerSupabase();
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();
    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const result = await validateProviderKey(service, api_key);
    return NextResponse.json(result, { status: 200 });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("/api/keys/validate POST error:", { message });
    return NextResponse.json(
      { error: "Internal server error", code: "INTERNAL_ERROR" },
      { status: 500 }
    );
  }
}
