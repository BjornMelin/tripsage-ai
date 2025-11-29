/**
 * @fileoverview Itinerary agent route handler (frontend-only).
 * - Supabase SSR auth → userId
 * - Provider resolution (BYOK/Gateway)
 * - Guardrails (cache, ratelimit, telemetry) around tools
 * - AI SDK v6 streaming with tool calls
 */

import "server-only";

import { resolveProvider } from "@ai/models/registry";
import { agentSchemas } from "@schemas/agents";
import type { NextRequest } from "next/server";
import { resolveAgentConfig } from "@/lib/agents/config-resolver";
import { createErrorHandler } from "@/lib/agents/error-recovery";
import { runItineraryAgent } from "@/lib/agents/itinerary-agent";
import { withApiGuards } from "@/lib/api/factory";
import { parseJsonBody, requireUserId, validateSchema } from "@/lib/api/route-helpers";

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
  const userResult = requireUserId(user);
  if ("error" in userResult) return userResult.error;
  const { userId } = userResult;

  const parsed = await parseJsonBody(req);
  if ("error" in parsed) {
    return parsed.error;
  }

  const validation = validateSchema(RequestSchema, parsed.body);
  if ("error" in validation) {
    return validation.error;
  }
  const body = validation.data;

  const modelHint = new URL(req.url).searchParams.get("model") ?? undefined;
  const resolved = await resolveAgentConfig("itineraryAgent");
  const agentConfig = resolved.config;
  const resolvedModelHint = agentConfig.model ?? modelHint;
  const { model, modelId } = await resolveProvider(userId, resolvedModelHint);

  const identifier = userId;
  const result = await runItineraryAgent(
    { identifier, model, modelId },
    agentConfig,
    body
  );
  return result.toUIMessageStreamResponse({
    onError: createErrorHandler(),
  });
});
