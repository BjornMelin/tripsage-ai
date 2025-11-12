/**
 * @fileoverview Router agent route handler (frontend-only).
 * - Supabase SSR auth → userId
 * - Provider resolution (BYOK/Gateway)
 * - Classifies user messages into agent workflows
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { classifyUserMessage } from "@/lib/agents/router-agent";
import {
  errorResponse,
  getTrustedRateLimitIdentifier,
  withRequestSpan,
} from "@/lib/next/route-helpers";
import { resolveProvider } from "@/lib/providers/registry";
import { enforceRouteRateLimit } from "@/lib/ratelimit/config";
import { getRedis } from "@/lib/redis";
import { createServerSupabase } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";
export const maxDuration = 30;

/**
 * POST /api/agents/router
 *
 * Classifies user message into an agent workflow.
 */
export async function POST(req: NextRequest): Promise<Response> {
  try {
    const supabase = await createServerSupabase();
    const user = (await supabase.auth.getUser()).data.user;

    const raw = (await req.json().catch(() => ({}))) as unknown;
    const body = raw as { message?: string };
    const message = body.message;
    if (!message || typeof message !== "string") {
      return errorResponse({
        error: "invalid_request",
        reason: "message field is required and must be a string",
        status: 400,
      });
    }

    const identifier = user?.id ?? getTrustedRateLimitIdentifier(req);
    const rateLimitError = await enforceRouteRateLimit("router", identifier, getRedis);
    if (rateLimitError) {
      return errorResponse(rateLimitError);
    }

    const modelHint = new URL(req.url).searchParams.get("model") ?? undefined;
    const { model, modelId } = await resolveProvider(user?.id ?? "anon", modelHint);

    const classification = await withRequestSpan(
      "agent.router",
      {
        identifier_type: user?.id ? "user" : "ip",
        modelId,
        workflow: "router",
      },
      () => classifyUserMessage({ model }, message)
    );

    return NextResponse.json(classification);
  } catch (err) {
    return errorResponse({
      err,
      error: "internal",
      reason: "Internal server error",
      status: 500,
    });
  }
}
