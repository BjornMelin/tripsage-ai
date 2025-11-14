/**
 * @fileoverview Hardened Next.js route handler for streaming chat responses.
 * - SSR auth via Supabase cookies
 * - Upstash Ratelimit sliding window (40/min)
 * - Provider registry + BYOK (SSR-only)
 * - Token clamping + usage metadata via messageMetadata
 * - Attachments mapping (image-only) and basic validation
 * - Minimal structured logs with redaction (no prompt logging)
 */

import "server-only";

import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";
import type { UIMessage } from "ai";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { getClientIpFromHeaders } from "@/lib/next/route-helpers";
import { resolveProvider } from "@/lib/providers/registry";
import { createServerSupabase } from "@/lib/supabase/server";
import { handleChatStream } from "./_handler";

// Avoid public caching; this route depends on auth/session
export const dynamic = "force-dynamic";

// Allow streaming responses for up to 60 seconds
export const maxDuration = 60;

const RATELIMIT_PREFIX = "ratelimit:chat";
let cachedLimiter: InstanceType<typeof Ratelimit> | undefined;

/**
 * Lazily construct (and cache) the Upstash rate limiter. Avoid module-scope
 * construction to keep tests deterministic and allow env stubbing.
 */
import { getServerEnvVarWithFallback } from "@/lib/env/server";

function getRateLimiter(): InstanceType<typeof Ratelimit> | undefined {
  if (cachedLimiter) return cachedLimiter;
  const url = getServerEnvVarWithFallback("UPSTASH_REDIS_REST_URL", undefined);
  const token = getServerEnvVarWithFallback("UPSTASH_REDIS_REST_TOKEN", undefined);
  if (!url || !token) return undefined;
  cachedLimiter = new Ratelimit({
    analytics: true,
    limiter: Ratelimit.slidingWindow(40, "1 m"),
    prefix: RATELIMIT_PREFIX,
    redis: Redis.fromEnv(),
  });
  return cachedLimiter;
}

/**
 * Type definition for the incoming request body structure.
 */
type IncomingBody = {
  messages?: UIMessage[];
  sessionId?: string;
  model?: string;
  desiredMaxTokens?: number;
};

/**
 * Handles POST requests for streaming chat responses with AI SDK.
 *
 * Performs authentication, rate limiting, provider resolution, token budgeting,
 * memory integration, and streams AI responses with comprehensive error handling
 * and usage metadata.
 *
 * @param req - The Next.js request object.
 * @returns Promise resolving to a Response with streamed chat data.
 */
export async function POST(req: NextRequest): Promise<Response> {
  try {
    const supabase = await createServerSupabase();

    // Parse
    let body: IncomingBody | undefined;
    try {
      body = (await req.json()) as IncomingBody;
    } catch {
      body = { messages: [] };
    }
    const ip = getClientIpFromHeaders(req);
    const limiter = getRateLimiter();
    return handleChatStream(
      {
        clock: { now: () => Date.now() },
        config: { defaultMaxTokens: 1024 },
        limit: limiter ? (id) => limiter.limit(id) : undefined,
        logger: { error: console.error, info: console.info },
        resolveProvider: (userId, modelHint) => resolveProvider(userId, modelHint),
        supabase,
      },
      { ...body, ip }
    );
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("/api/chat/stream:fatal", { message });
    return NextResponse.json({ error: "internal" }, { status: 500 });
  }
}
