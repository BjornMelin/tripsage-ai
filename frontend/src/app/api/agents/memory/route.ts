/**
 * @fileoverview Memory agent route handler (frontend-only).
 * - Supabase SSR auth → userId
 * - Provider resolution (BYOK/Gateway)
 * - Guardrails (cache, ratelimit, telemetry) around tools
 * - AI SDK v6 streaming with tool calls
 */

import "server-only";

import { resolveProvider } from "@ai/models/registry";
import type { MemoryUpdateRequest } from "@schemas/agents";
import { agentSchemas } from "@schemas/agents";
import type { NextRequest } from "next/server";
import type { z } from "zod";
import { resolveAgentConfig } from "@/lib/agents/config-resolver";
import { createErrorHandler } from "@/lib/agents/error-recovery";
import { runMemoryAgent } from "@/lib/agents/memory-agent";
import { withApiGuards } from "@/lib/api/factory";
import {
  errorResponse,
  getTrustedRateLimitIdentifier,
  parseJsonBody,
} from "@/lib/next/route-helpers";

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
  const parsed = await parseJsonBody(req);
  if ("error" in parsed) {
    return parsed.error;
  }

  let body: MemoryUpdateRequest;
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

  const identifier = user?.id ?? getTrustedRateLimitIdentifier(req);
  const config = await resolveAgentConfig("memoryAgent");
  const modelHint =
    config.config.model ?? new URL(req.url).searchParams.get("model") ?? undefined;
  const { model, modelId } = await resolveProvider(user?.id ?? "anon", modelHint);

  const result = await runMemoryAgent(
    { identifier, model, modelId },
    config.config,
    body
  );
  return result.toUIMessageStreamResponse({
    onError: createErrorHandler(),
  });
});
