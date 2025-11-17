/**
 * @fileoverview Router agent route handler (frontend-only).
 * - Supabase SSR auth → userId
 * - Provider resolution (BYOK/Gateway)
 * - Classifies user messages into agent workflows
 */

import "server-only";

import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import type { z } from "zod";
import { classifyUserMessage } from "@/lib/agents/router-agent";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse } from "@/lib/next/route-helpers";
import { resolveProvider } from "@/lib/providers/registry";
import type { RouterRequest } from "@/lib/schemas/agents";
import { agentSchemas } from "@/lib/schemas/agents";

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
  auth: false,
  rateLimit: "agents:router",
  telemetry: "agent.router",
})(async (req: NextRequest, { user }) => {
  const raw = (await req.json().catch(() => ({}))) as unknown;
  let body: RouterRequest;
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

  const modelHint = new URL(req.url).searchParams.get("model") ?? undefined;
  const { model } = await resolveProvider(user?.id ?? "anon", modelHint);

  const classification = await classifyUserMessage({ model }, body.message);

  return NextResponse.json(classification);
});
