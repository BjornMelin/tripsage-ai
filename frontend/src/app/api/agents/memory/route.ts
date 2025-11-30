/**
 * @fileoverview Memory agent route handler (frontend-only).
 * - Supabase SSR auth → userId
 * - Provider resolution (BYOK/Gateway)
 * - Guardrails (cache, ratelimit, telemetry) around tools
 * - AI SDK v6 streaming with tool calls
 */

import "server-only";

import { runMemoryAgent } from "@ai/agents/memory-agent";
import { resolveProvider } from "@ai/models/registry";
import { agentSchemas } from "@schemas/agents";
import type { NextRequest } from "next/server";
import { resolveAgentConfig } from "@/lib/agents/config-resolver";
import { createErrorHandler } from "@/lib/agents/error-recovery";
import { withApiGuards } from "@/lib/api/factory";
import { parseJsonBody, requireUserId, validateSchema } from "@/lib/api/route-helpers";

export const maxDuration = 60;

const RequestSchema = agentSchemas.memoryUpdateRequestSchema;

/**
 * POST /api/agents/memory
 *
 * Validates request, resolves provider, and streams ToolLoop response.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "agents:memory",
  telemetry: "agent.memoryUpdate",
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

  const config = await resolveAgentConfig("memoryAgent");
  const modelHint =
    config.config.model ?? new URL(req.url).searchParams.get("model") ?? undefined;
  const { model, modelId } = await resolveProvider(userId, modelHint);

  const result = await runMemoryAgent(
    { identifier: userId, model, modelId },
    config.config,
    body
  );
  return result.toUIMessageStreamResponse({
    onError: createErrorHandler(),
  });
});
