/**
 * @fileoverview BYOK validate route. Checks if a provided API key is valid for a given service.
 * Route: POST /api/keys/validate
 * Never persists the key.
 */

"use cache";

export const dynamic = "force-dynamic";

import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { getClientIpFromHeaders } from "@/lib/next/route-helpers";
import { createServerSupabase } from "@/lib/supabase/server";

// Environment variables
const UPSTASH_URL = process.env.UPSTASH_REDIS_REST_URL;
const UPSTASH_TOKEN = process.env.UPSTASH_REDIS_REST_TOKEN;
const RATELIMIT_PREFIX = "ratelimit:keys-validate";

// Create rate limit instance lazily to make testing easier
const GET_RATELIMIT_INSTANCE = () => {
  if (!UPSTASH_URL || !UPSTASH_TOKEN) {
    return undefined;
  }

  return new Ratelimit({
    analytics: true,
    limiter: Ratelimit.slidingWindow(20, "1 m"),
    prefix: RATELIMIT_PREFIX,
    redis: Redis.fromEnv(),
  });
};

type ProviderConfig = {
  url: string;
  buildHeaders: (apiKey: string) => Record<string, string>;
};

const PROVIDERS: Record<string, ProviderConfig> = {
  anthropic: {
    buildHeaders: (key) => ({
      "anthropic-version": "2023-06-01",
      "x-api-key": key,
    }),
    url: "https://api.anthropic.com/v1/models",
  },
  openai: {
    buildHeaders: (key) => ({
      Authorization: `Bearer ${key}`,
    }),
    url: "https://api.openai.com/v1/models",
  },
  openrouter: {
    buildHeaders: (key) => ({
      Authorization: `Bearer ${key}`,
    }),
    url: "https://openrouter.ai/api/v1/models",
  },
  xai: {
    buildHeaders: (key) => ({
      Authorization: `Bearer ${key}`,
    }),
    url: "https://api.x.ai/v1/models",
  },
};

type ValidateResult = { isValid: boolean; reason?: string };

/**
 * Generic validator using provider configuration map.
 *
 * @param service Provider identifier (openai|openrouter|anthropic|xai).
 * @param apiKey The plaintext API key to check.
 * @returns Validation result with is_valid and optional reason.
 */
async function validateProviderKey(
  service: string,
  apiKey: string
): Promise<ValidateResult> {
  const cfg = PROVIDERS[service.trim().toLowerCase()];
  if (!cfg) return { isValid: false, reason: `Invalid service: ${service}` };

  try {
    const res = await fetch(cfg.url, {
      headers: cfg.buildHeaders(apiKey),
      method: "GET",
    });
    if (res.status === 200) return { isValid: true };
    if ([401, 403].includes(res.status))
      return { isValid: false, reason: "Unauthorized" };
    return { isValid: false, reason: `HTTP_${res.status}` };
  } catch {
    return { isValid: false, reason: "NETWORK_ERROR" };
  }
}

/**
 * Require rate limiting for the request.
 *
 * @param req Next.js request object.
 * @returns NextResponse with 429 status if rate limit exceeded, otherwise null.
 */
async function requireRateLimit(identifier: string): Promise<NextResponse | null> {
  const ratelimitInstance = GET_RATELIMIT_INSTANCE();
  if (!ratelimitInstance) return null;
  const { success, limit, remaining, reset } =
    await ratelimitInstance.limit(identifier);
  if (!success) {
    return NextResponse.json(
      { code: "RATE_LIMIT", error: "Rate limit exceeded" },
      {
        headers: {
          "X-RateLimit-Limit": String(limit),
          "X-RateLimit-Remaining": String(remaining),
          "X-RateLimit-Reset": String(reset),
        },
        status: 429,
      }
    );
  }
  return null;
}

/**
 * Require authenticated user.
 *
 * @returns NextResponse with 401 status if user not authenticated, otherwise user ID.
 */
/**
 * Handle POST /api/keys/validate to verify a user-supplied API key.
 *
 * Orchestrates rate limiting, authentication, and provider validation.
 *
 * @param req Next.js request containing JSON body with { service, apiKey }.
 * @returns 200 with validation result; 400/401/429/500 on error.
 */
export async function POST(req: NextRequest) {
  try {
    const supabase = await createServerSupabase();
    const {
      data: { user },
      error,
    } = await supabase.auth.getUser();
    const identifier = user?.id ?? getClientIpFromHeaders(req.headers);

    const rateLimitResponse = await requireRateLimit(identifier);
    if (rateLimitResponse) {
      return rateLimitResponse;
    }

    let service: string | undefined;
    let apiKey: string | undefined;
    try {
      const body = await req.json();
      service = body.service;
      apiKey = body.apiKey;
    } catch (parseError) {
      const message =
        parseError instanceof Error ? parseError.message : "Unknown JSON parse error";
      console.error("/api/keys/validate POST JSON parse error:", { message });
      return NextResponse.json(
        { code: "BAD_REQUEST", error: "Malformed JSON in request body" },
        { status: 400 }
      );
    }

    if (
      !service ||
      !apiKey ||
      typeof service !== "string" ||
      typeof apiKey !== "string"
    ) {
      return NextResponse.json(
        { code: "BAD_REQUEST", error: "Invalid request body" },
        { status: 400 }
      );
    }

    if (error || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const result = await validateProviderKey(service, apiKey);
    return NextResponse.json(result, { status: 200 });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("/api/keys/validate POST error:", { message });
    return NextResponse.json(
      { code: "INTERNAL_ERROR", error: "Internal server error" },
      { status: 500 }
    );
  }
}
