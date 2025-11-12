/**
 * @fileoverview Itinerary agent route handler (frontend-only).
 * - Supabase SSR auth → userId
 * - Provider resolution (BYOK/Gateway)
 * - Guardrails (cache, ratelimit, telemetry) around tools
 * - AI SDK v6 streaming with tool calls
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import type { z } from "zod";
import { createErrorHandler } from "@/lib/agents/error-recovery";
import { runItineraryAgent } from "@/lib/agents/itinerary-agent";
import { getTrustedRateLimitIdentifier } from "@/lib/next/route-helpers";
import { resolveProvider } from "@/lib/providers/registry";
import { enforceRouteRateLimit } from "@/lib/ratelimit/config";
import { getRedis } from "@/lib/redis";
import { createServerSupabase } from "@/lib/supabase/server";
import type { ItineraryPlanRequest } from "@/schemas/agents";
import { agentSchemas } from "@/schemas/agents";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

const RequestSchema = agentSchemas.itineraryPlanRequestSchema;

/**
 * POST /api/agents/itineraries
 *
 * Validates request, resolves provider, and streams ToolLoop response.
 */
export async function POST(req: NextRequest): Promise<Response> {
  try {
    const supabase = await createServerSupabase();
    const user = (await supabase.auth.getUser()).data.user;

    const raw = (await req.json().catch(() => ({}))) as unknown;
    let body: ItineraryPlanRequest;
    try {
      body = RequestSchema.parse(raw);
    } catch (err) {
      const zerr = err as z.ZodError;
      return NextResponse.json(
        { error: "invalid_request", issues: zerr.issues },
        { status: 400 }
      );
    }

    const modelHint = new URL(req.url).searchParams.get("model") ?? undefined;
    const { model } = await resolveProvider(user?.id ?? "anon", modelHint);
    const identifier = user?.id ?? getTrustedRateLimitIdentifier(req);

    const rateLimitError = await enforceRouteRateLimit(
      "itineraryPlanning",
      identifier,
      getRedis
    );
    if (rateLimitError) {
      return NextResponse.json(
        { error: rateLimitError.error, reason: rateLimitError.reason },
        { status: rateLimitError.status }
      );
    }

    const result = runItineraryAgent({ identifier, model }, body);
    return result.toUIMessageStreamResponse({
      onError: createErrorHandler(),
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("/api/agents/itineraries:fatal", { message });
    return NextResponse.json({ error: "internal" }, { status: 500 });
  }
}
