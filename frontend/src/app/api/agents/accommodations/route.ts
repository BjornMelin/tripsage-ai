/**
 * @fileoverview Accommodation agent route handler using AI SDK v6 ToolLoopAgent.
 * - Supabase SSR auth → userId
 * - Provider resolution (BYOK/Gateway)
 * - Guardrails (cache, ratelimit, telemetry) around tools
 * - AI SDK v6 ToolLoopAgent with createAgentUIStreamResponse
 */

import "server-only";

import { createAccommodationAgent } from "@ai/agents";
import { resolveProvider } from "@ai/models/registry";
import type { AccommodationSearchRequest } from "@schemas/agents";
import { agentSchemas } from "@schemas/agents";
import { createAgentUIStreamResponse } from "ai";
import type { NextRequest } from "next/server";
import { resolveAgentConfig } from "@/lib/agents/config-resolver";
import { createErrorHandler } from "@/lib/agents/error-recovery";
import { withApiGuards } from "@/lib/api/factory";
import { requireUserId } from "@/lib/api/route-helpers";

export const maxDuration = 60;

const RequestSchema = agentSchemas.accommodationSearchRequestSchema;

/**
 * POST /api/agents/accommodations
 *
 * Validates request, resolves provider, and streams ToolLoopAgent response.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "agents:accommodations",
  schema: RequestSchema,
  telemetry: "agent.accommodationSearch",
})(async (req: NextRequest, context, body: AccommodationSearchRequest) => {
  const { user } = context;
  const userResult = requireUserId(user);
  if ("error" in userResult) return userResult.error;
  const { userId } = userResult;

  const config = await resolveAgentConfig("accommodationAgent");
  const modelHint =
    config.config.model ?? new URL(req.url).searchParams.get("model") ?? undefined;
  const { model, modelId } = await resolveProvider(userId, modelHint);

  const { agent, defaultMessages } = createAccommodationAgent(
    { identifier: userId, model, modelId },
    config.config,
    body
  );

  return createAgentUIStreamResponse({
    agent,
    messages: defaultMessages,
    onError: createErrorHandler(),
  });
});
