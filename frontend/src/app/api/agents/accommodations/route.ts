/**
 * @fileoverview Accommodation agent route handler (frontend-only).
 * - Supabase SSR auth → userId
 * - Provider resolution (BYOK/Gateway)
 * - Guardrails (cache, ratelimit, telemetry) around tools
 * - AI SDK v6 streaming with tool calls
 */

import "server-only";

import type { NextRequest } from "next/server";
import type { z } from "zod";
import { runAccommodationAgent } from "@/lib/agents/accommodation-agent";
import { createErrorHandler } from "@/lib/agents/error-recovery";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, getTrustedRateLimitIdentifier } from "@/lib/next/route-helpers";
import { resolveProvider } from "@/lib/providers/registry";
import type { AccommodationSearchRequest } from "@/lib/schemas/agents";
import { agentSchemas } from "@/lib/schemas/agents";

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
  telemetry: "agent.accommodationSearch",
})(async (req: NextRequest, { user }) => {
  const raw = (await req.json().catch(() => ({}))) as unknown;
  let body: AccommodationSearchRequest;
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
  const { model, modelId } = await resolveProvider(user?.id ?? "anon", modelHint);

  const result = runAccommodationAgent({ identifier, model, modelId }, body);
  return result.toUIMessageStreamResponse({
    onError: createErrorHandler(),
  });
});
