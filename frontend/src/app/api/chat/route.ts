/**
 * @fileoverview Next.js Route Handler for non-streaming chat responses.
 * Thin adapter: SSR auth via Supabase, provider resolution, token clamping
 * through DI handler, and safe JSON response with usage metadata.
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
import { handleChatNonStream } from "./_handler";

// Dynamic due to auth/session
export const dynamic = "force-dynamic";

// Allow up to 30s for non-stream completion
export const maxDuration = 30;

/**
 * Type representing the incoming body for the chat route.
 * 
 * @param messages - The messages.
 * @param session_id - The session ID.
 * @param model - The model.
 * @param desiredMaxTokens - The desired maximum tokens.
 */
type IncomingBody = {
  messages?: UIMessage[];
  session_id?: string;
  model?: string;
  desiredMaxTokens?: number;
};

/**
 * Handles POST requests for chat responses.
 *
 * @param req - The Next.js request object.
 * @returns Promise resolving to a Response with chat completion data.
 */
export async function POST(req: NextRequest): Promise<Response> {
  try {
    const supabase = await createServerSupabase();

    let body: IncomingBody | undefined;
    try {
      body = (await req.json()) as IncomingBody;
    } catch {
      body = { messages: [] };
    }

    // Optional rate limiter (reuse stream config if available)
    const url = process.env.UPSTASH_REDIS_REST_URL;
    const token = process.env.UPSTASH_REDIS_REST_TOKEN;
    const limiter =
      url && token
        ? new Ratelimit({
            redis: Redis.fromEnv(),
            limiter: Ratelimit.slidingWindow(40, "1 m"),
            analytics: true,
            prefix: "ratelimit:chat:nonstream",
          })
        : undefined;

    const ip = getClientIpFromHeaders(req.headers);

    const response = await handleChatNonStream(
      {
        supabase,
        resolveProvider: (userId, modelHint) => resolveProvider(userId, modelHint),
        logger: { info: console.info, error: console.error },
        clock: { now: () => Date.now() },
        config: { defaultMaxTokens: 1024 },
        limit: limiter ? (id) => limiter.limit(id) : undefined,
      },
      { ...body!, ip }
    );
    return response;
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("/api/chat:fatal", { message });
    return NextResponse.json({ error: "internal" }, { status: 500 });
  }
}
