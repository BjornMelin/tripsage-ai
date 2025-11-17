/**
 * @fileoverview Memory agent route handler (frontend-only).
 * - Supabase SSR auth → userId
 * - Provider resolution (BYOK/Gateway)
 * - Guardrails (cache, ratelimit, telemetry) around tools
 * - AI SDK v6 streaming with tool calls
 */

import "server-only";

import type { NextRequest } from "next/server";
import type { z } from "zod";
import { createErrorHandler } from "@/lib/agents/error-recovery";
import { runMemoryAgent } from "@/lib/agents/memory-agent";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, getTrustedRateLimitIdentifier } from "@/lib/next/route-helpers";
import { resolveProvider } from "@/lib/providers/registry";
import type { MemoryUpdateRequest } from "@/lib/schemas/agents";
import { agentSchemas } from "@/lib/schemas/agents";

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
  const raw = (await req.json().catch(() => ({}))) as unknown;
  let body: MemoryUpdateRequest;
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
  const modelHint = new URL(req.url).searchParams.get("model") ?? undefined;
  const { model } = await resolveProvider(user?.id ?? "anon", modelHint);

  const result = await runMemoryAgent({ identifier, model }, body);
  return result.toUIMessageStreamResponse({
    onError: createErrorHandler(),
  });
});
