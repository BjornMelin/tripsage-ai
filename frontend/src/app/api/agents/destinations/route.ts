/**
 * @fileoverview Destination agent route handler (frontend-only).
 * - Supabase SSR auth → userId
 * - Provider resolution (BYOK/Gateway)
 * - Guardrails (cache, ratelimit, telemetry) around tools
 * - AI SDK v6 streaming with tool calls
 */

import "server-only";

import type { DestinationResearchRequest } from "@schemas/agents";
import { agentSchemas } from "@schemas/agents";
import type { NextRequest } from "next/server";
import type { z } from "zod";
import { runDestinationAgent } from "@/lib/agents/destination-agent";
import { createErrorHandler } from "@/lib/agents/error-recovery";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, parseJsonBody } from "@/lib/next/route-helpers";
import { resolveProvider } from "@/lib/providers/registry";

export const maxDuration = 60;

const RequestSchema = agentSchemas.destinationResearchRequestSchema;

/**
 * POST /api/agents/destinations
 *
 * Validates request, resolves provider, and streams ToolLoop response.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "agents:destinations",
  telemetry: "agent.destinationResearch",
})(async (req: NextRequest, { user }) => {
  const parsed = await parseJsonBody(req);
  if ("error" in parsed) {
    return parsed.error;
  }

  let body: DestinationResearchRequest;
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
  const { model, modelId } = await resolveProvider(user?.id ?? "anon", modelHint);

  const result = runDestinationAgent({ model, modelId }, body);
  return result.toUIMessageStreamResponse({
    onError: createErrorHandler(),
  });
});
