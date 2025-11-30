/**
 * @fileoverview Router agent route handler (frontend-only).
 * - Supabase SSR auth → userId
 * - Provider resolution (BYOK/Gateway)
 * - Classifies user messages into agent workflows
 */

import "server-only";

import { classifyUserMessage } from "@ai/agents/router-agent";
import { resolveProvider } from "@ai/models/registry";
import { agentSchemas } from "@schemas/agents";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { parseJsonBody, requireUserId, validateSchema } from "@/lib/api/route-helpers";

export const maxDuration = 30;

const RequestSchema = agentSchemas.routerRequestSchema;

/**
 * POST /api/agents/router
 *
 * Classifies user message into an agent workflow.
 *
 * @param req - Next.js request object
 * @param routeContext - Route context from withApiGuards
 * @returns JSON response with classification result
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "agents:router",
  telemetry: "agent.router",
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

  const modelHint = new URL(req.url).searchParams.get("model") ?? undefined;
  const { model } = await resolveProvider(userId, modelHint);

  const classification = await classifyUserMessage({ model }, body.message);

  return NextResponse.json(classification);
});
