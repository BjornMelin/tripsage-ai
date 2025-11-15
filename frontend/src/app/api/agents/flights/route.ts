/**
 * @fileoverview Flight agent route handler (frontend-only).
 * - Supabase SSR auth → userId
 * - Provider resolution (BYOK/Gateway)
 * - Guardrails (cache, ratelimit, telemetry) around tools
 * - AI SDK v6 streaming with tool calls
 */

import "server-only";

import type { NextRequest } from "next/server";
import type { z } from "zod";
import { createErrorHandler } from "@/lib/agents/error-recovery";
import { runFlightAgent } from "@/lib/agents/flight-agent";
import {
  errorResponse,
  getTrustedRateLimitIdentifier,
  withRequestSpan,
} from "@/lib/next/route-helpers";
import { resolveProvider } from "@/lib/providers/registry";
import { enforceRouteRateLimit } from "@/lib/ratelimit/config";
import { getRedis } from "@/lib/redis";
import type { FlightSearchRequest } from "@/lib/schemas/agents";
import { agentSchemas } from "@/lib/schemas/agents";
import { createServerSupabase } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

const RequestSchema = agentSchemas.flightSearchRequestSchema;

/**
 * POST /api/agents/flights
 *
 * Validates request, resolves provider, and streams ToolLoop response.
 */
export async function POST(req: NextRequest): Promise<Response> {
  try {
    const supabase = await createServerSupabase();
    const user = (await supabase.auth.getUser()).data.user;

    const raw = (await req.json().catch(() => ({}))) as unknown;
    let body: FlightSearchRequest;
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

    // Route-level rate limiting using centralized config
    const rateLimitError = await enforceRouteRateLimit(
      "flightSearch",
      identifier,
      getRedis
    );
    if (rateLimitError) {
      return errorResponse(rateLimitError);
    }

    const modelHint = new URL(req.url).searchParams.get("model") ?? undefined;
    const { model, modelId } = await resolveProvider(user?.id ?? "anon", modelHint);

    return await withRequestSpan(
      "agent.flightSearch",
      {
        identifier_type: user?.id ? "user" : "ip",
        modelId,
        workflow: "flightSearch",
      },
      (): Promise<Response> => {
        const result = runFlightAgent({ identifier, model }, body);
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
