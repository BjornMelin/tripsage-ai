/**
 * @fileoverview Accommodation agent route handler (frontend-only).
 * - Supabase SSR auth → userId
 * - Provider resolution (BYOK/Gateway)
 * - Guardrails (cache, ratelimit, telemetry) around tools
 * - AI SDK v6 streaming with tool calls
 */

import "server-only";

import { resolveProvider } from "@ai/models/registry";
import type { AccommodationSearchRequest } from "@schemas/agents";
import { agentSchemas } from "@schemas/agents";
import type { NextRequest } from "next/server";
import { runAccommodationAgent } from "@/lib/agents/accommodation-agent";
import { resolveAgentConfig } from "@/lib/agents/config-resolver";
import { withApiGuards } from "@/lib/api/factory";
import { requireUserId } from "@/lib/api/route-helpers";

export const maxDuration = 60;

const RequestSchema = agentSchemas.accommodationSearchRequestSchema;

/**
 * POST /api/agents/accommodations
 *
 * Validates request, resolves provider, and streams ToolLoop response.
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

  const result = await runAccommodationAgent(
    { identifier: userId, model, modelId },
    config.config,
    body
  );
  return result.toTextStreamResponse({
    headers: { "Content-Type": "text/event-stream" },
  });
});
