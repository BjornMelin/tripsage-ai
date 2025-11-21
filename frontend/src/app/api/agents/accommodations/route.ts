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
import { withApiGuards } from "@/lib/api/factory";
import { getTrustedRateLimitIdentifier } from "@/lib/next/route-helpers";

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
  const identifier = user?.id ?? getTrustedRateLimitIdentifier(req);
  const modelHint = new URL(req.url).searchParams.get("model") ?? undefined;
  const { model, modelId } = await resolveProvider(user?.id ?? "anon", modelHint);

  const result = runAccommodationAgent({ identifier, model, modelId }, body);
  return result.toTextStreamResponse({
    headers: { "Content-Type": "text/event-stream" },
  });
});
