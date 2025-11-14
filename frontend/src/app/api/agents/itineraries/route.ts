/**
 * @fileoverview Itinerary agent route handler (frontend-only).
 * - Supabase SSR auth → userId
 * - Provider resolution (BYOK/Gateway)
 * - Guardrails (cache, ratelimit, telemetry) around tools
 * - AI SDK v6 streaming with tool calls
 */

import "server-only";

import type { NextRequest } from "next/server";
import type { z } from "zod";
import { createErrorHandler } from "@/lib/agents/error-recovery";
import { runItineraryAgent } from "@/lib/agents/itinerary-agent";
import {
  errorResponse,
  getTrustedRateLimitIdentifier,
  withRequestSpan,
} from "@/lib/next/route-helpers";
import { resolveProvider } from "@/lib/providers/registry";
import { enforceRouteRateLimit } from "@/lib/ratelimit/config";
import { getRedis } from "@/lib/redis";
import type { ItineraryPlanRequest } from "@/lib/schemas/agents";
import { agentSchemas } from "@/lib/schemas/agents";
import { createServerSupabase } from "@/lib/supabase";

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
      return errorResponse({
        err: zerr,
        error: "invalid_request",
        issues: zerr.issues,
        reason: "Request validation failed",
        status: 400,
      });
    }

    const identifier = user?.id ?? getTrustedRateLimitIdentifier(req);

    const rateLimitError = await enforceRouteRateLimit(
      "itineraryPlanning",
      identifier,
      getRedis
    );
    if (rateLimitError) {
      return errorResponse(rateLimitError);
    }

    const modelHint = new URL(req.url).searchParams.get("model") ?? undefined;
    const { model, modelId } = await resolveProvider(user?.id ?? "anon", modelHint);

    return await withRequestSpan(
      "agent.itineraryPlanning",
      {
        identifier_type: user?.id ? "user" : "ip",
        modelId,
        workflow: "itineraryPlanning",
      },
      (): Promise<Response> => {
        const result = runItineraryAgent({ identifier, model }, body);
        return Promise.resolve(
          result.toUIMessageStreamResponse({
            onError: createErrorHandler(),
          })
        );
      }
    );
  } catch (err) {
    return errorResponse({
      err,
      error: "internal",
      reason: "Internal server error",
      status: 500,
    });
  }
}
