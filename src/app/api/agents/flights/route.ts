/**
 * @fileoverview Flight agent route handler using AI SDK v6 ToolLoopAgent.
 * - Supabase SSR auth → userId
 * - Provider resolution (BYOK/Gateway)
 * - Guardrails (cache, ratelimit, telemetry) around tools
 * - AI SDK v6 ToolLoopAgent with createAgentUIStreamResponse
 */

import "server-only";

import { createFlightAgent } from "@ai/agents";
import { resolveProvider } from "@ai/models/registry";
import { flightSearchRequestSchema } from "@schemas/flights";
import { createAgentUIStreamResponse } from "ai";
import type { NextRequest } from "next/server";
import { resolveAgentConfig } from "@/lib/agents/config-resolver";
import { createErrorHandler } from "@/lib/agents/error-recovery";
import { withApiGuards } from "@/lib/api/factory";
import { parseJsonBody, requireUserId, validateSchema } from "@/lib/api/route-helpers";

export const maxDuration = 60;

const RequestSchema = flightSearchRequestSchema;

/**
 * POST /api/agents/flights
 *
 * Validates request, resolves provider, and streams ToolLoopAgent response.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "agents:flight",
  telemetry: "agent.flightSearch",
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

  const config = await resolveAgentConfig("flightAgent");
  const modelHint =
    config.config.model ?? new URL(req.url).searchParams.get("model") ?? undefined;
  const { model, modelId } = await resolveProvider(userId, modelHint);

  const { agent, defaultMessages } = createFlightAgent(
    { identifier: userId, model, modelId, userId },
    config.config,
    body
  );

  return createAgentUIStreamResponse({
    agent,
    messages: defaultMessages,
    onError: createErrorHandler(),
  });
});
