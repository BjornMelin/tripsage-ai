/**
 * @fileoverview Budget agent route handler (frontend-only).
 * - Supabase SSR auth → userId
 * - Provider resolution (BYOK/Gateway)
 * - Guardrails (cache, ratelimit, telemetry) around tools
 * - AI SDK v6 streaming with tool calls
 */

import "server-only";

import { resolveProvider } from "@ai/models/registry";
import type { BudgetPlanRequest } from "@schemas/agents";
import { agentSchemas } from "@schemas/agents";
import type { NextRequest } from "next/server";
import type { z } from "zod";
import { runBudgetAgent } from "@/lib/agents/budget-agent";
import { resolveAgentConfig } from "@/lib/agents/config-resolver";
import { createErrorHandler } from "@/lib/agents/error-recovery";
import { withApiGuards } from "@/lib/api/factory";
import {
  errorResponse,
  getTrustedRateLimitIdentifier,
  parseJsonBody,
} from "@/lib/next/route-helpers";

export const maxDuration = 60;

const RequestSchema = agentSchemas.budgetPlanRequestSchema;

/**
 * POST /api/agents/budget
 *
 * Validates request, resolves provider, and streams ToolLoop response.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "agents:budget",
  telemetry: "agent.budgetPlanning",
})(async (req: NextRequest, { user }) => {
  const parsed = await parseJsonBody(req);
  if ("error" in parsed) {
    return parsed.error;
  }

  let body: BudgetPlanRequest;
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
  const config = await resolveAgentConfig("budgetAgent");
  const modelHint =
    config.config.model ?? new URL(req.url).searchParams.get("model") ?? undefined;
  const { model, modelId } = await resolveProvider(user?.id ?? "anon", modelHint);

  const result = runBudgetAgent({ identifier, model, modelId }, config.config, body);
  return result.toUIMessageStreamResponse({
    onError: createErrorHandler(),
  });
});
