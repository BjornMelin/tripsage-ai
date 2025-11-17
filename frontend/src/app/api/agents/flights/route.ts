/**
 * @fileoverview Flight agent route handler (frontend-only).
 * - Supabase SSR auth → userId
 * - Provider resolution (BYOK/Gateway)
 * - Guardrails (cache, ratelimit, telemetry) around tools
 * - AI SDK v6 streaming with tool calls
 */

import "server-only";

import type { NextRequest } from "next/server";
import type { z } from "zod";
import { createErrorHandler } from "@/lib/agents/error-recovery";
import { runFlightAgent } from "@/lib/agents/flight-agent";
import { withApiGuards } from "@/lib/api/factory";
import {
  errorResponse,
  getTrustedRateLimitIdentifier,
  parseJsonBody,
} from "@/lib/next/route-helpers";
import { resolveProvider } from "@/lib/providers/registry";
import type { FlightSearchRequest } from "@/lib/schemas/agents";
import { agentSchemas } from "@/lib/schemas/agents";

export const maxDuration = 60;

const RequestSchema = agentSchemas.flightSearchRequestSchema;

/**
 * POST /api/agents/flights
 *
 * Validates request, resolves provider, and streams ToolLoop response.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "agents:flight",
  telemetry: "agent.flightSearch",
})(async (req: NextRequest, { user }) => {
  const parsed = await parseJsonBody(req);
  if ("error" in parsed) {
    return parsed.error;
  }

  let body: FlightSearchRequest;
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
  const modelHint = new URL(req.url).searchParams.get("model") ?? undefined;
  const { model, modelId } = await resolveProvider(user?.id ?? "anon", modelHint);

  const result = runFlightAgent({ identifier, model, modelId }, body);
  return result.toUIMessageStreamResponse({
    onError: createErrorHandler(),
  });
});
