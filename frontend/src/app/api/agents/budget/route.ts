/**
 * @fileoverview Budget agent route handler using AI SDK v6 ToolLoopAgent.
 * - Supabase SSR auth → userId
 * - Provider resolution (BYOK/Gateway)
 * - Guardrails (cache, ratelimit, telemetry) around tools
 * - AI SDK v6 ToolLoopAgent with createAgentUIStreamResponse
 */

import "server-only";

import { createBudgetAgent } from "@ai/agents";
import { resolveProvider } from "@ai/models/registry";
import { agentSchemas } from "@schemas/agents";
import { createAgentUIStreamResponse } from "ai";
import type { NextRequest } from "next/server";
import { resolveAgentConfig } from "@/lib/agents/config-resolver";
import { createErrorHandler } from "@/lib/agents/error-recovery";
import { withApiGuards } from "@/lib/api/factory";
import { parseJsonBody, requireUserId, validateSchema } from "@/lib/api/route-helpers";

export const maxDuration = 60;

const RequestSchema = agentSchemas.budgetPlanRequestSchema;

/**
 * POST /api/agents/budget
 *
 * Validates request, resolves provider, and streams ToolLoopAgent response.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "agents:budget",
  telemetry: "agent.budgetPlanning",
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

  const config = await resolveAgentConfig("budgetAgent");
  const modelHint =
    config.config.model ?? new URL(req.url).searchParams.get("model") ?? undefined;
  const { model, modelId } = await resolveProvider(userId, modelHint);

  const { agent, defaultMessages } = createBudgetAgent(
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
