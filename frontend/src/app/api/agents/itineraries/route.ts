/**
 * @fileoverview Itinerary agent route handler (frontend-only).
 * - Supabase SSR auth → userId
 * - Provider resolution (BYOK/Gateway)
 * - Guardrails (cache, ratelimit, telemetry) around tools
 * - AI SDK v6 streaming with tool calls
 */

import "server-only";

import { resolveProvider } from "@ai/models/registry";
import type { ItineraryPlanRequest } from "@schemas/agents";
import { agentSchemas } from "@schemas/agents";
import type { NextRequest } from "next/server";
import type { z } from "zod";
import { resolveAgentConfig } from "@/lib/agents/config-resolver";
import { createErrorHandler } from "@/lib/agents/error-recovery";
import { runItineraryAgent } from "@/lib/agents/itinerary-agent";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, parseJsonBody } from "@/lib/api/route-helpers";

export const maxDuration = 60;

const RequestSchema = agentSchemas.itineraryPlanRequestSchema;

/**
 * POST /api/agents/itineraries
 *
 * Validates request, resolves provider, and streams ToolLoop response.
 *
 * @param req - Next.js request object
 * @param routeContext - Route context from withApiGuards
 * @returns Streaming response with itinerary plan
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "agents:itineraries",
  telemetry: "agent.itineraryPlanning",
})(async (req: NextRequest, { user }) => {
  const parsed = await parseJsonBody(req);
  if ("error" in parsed) {
    return parsed.error;
  }

  let body: ItineraryPlanRequest;
  try {
    body = RequestSchema.parse(parsed.body);
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

  const modelHint = new URL(req.url).searchParams.get("model") ?? undefined;
  const resolved = await resolveAgentConfig("itineraryAgent");
  const agentConfig = resolved.config;
  const resolvedModelHint = agentConfig.model ?? modelHint;
  const { model, modelId } = await resolveProvider(
    user?.id ?? "anon",
    resolvedModelHint
  );

  const identifier = user?.id ?? "anon";
  const result = runItineraryAgent({ identifier, model, modelId }, agentConfig, body);
  return result.toUIMessageStreamResponse({
    onError: createErrorHandler(),
  });
});
