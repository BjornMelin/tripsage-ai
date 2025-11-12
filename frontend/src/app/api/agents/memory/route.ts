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
import {
  errorResponse,
  getTrustedRateLimitIdentifier,
  withRequestSpan,
} from "@/lib/next/route-helpers";
import { resolveProvider } from "@/lib/providers/registry";
import { enforceRouteRateLimit } from "@/lib/ratelimit/config";
import { getRedis } from "@/lib/redis";
import { createServerSupabase } from "@/lib/supabase/server";
import type { MemoryUpdateRequest } from "@/schemas/agents";
import { agentSchemas } from "@/schemas/agents";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

const RequestSchema = agentSchemas.memoryUpdateRequestSchema;

/**
 * POST /api/agents/memory
 *
 * Validates request, resolves provider, and streams ToolLoop response.
 */
export async function POST(req: NextRequest): Promise<Response> {
  try {
    const supabase = await createServerSupabase();
    const user = (await supabase.auth.getUser()).data.user;

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

    const rateLimitError = await enforceRouteRateLimit(
      "memoryUpdate",
      identifier,
      getRedis
    );
    if (rateLimitError) {
      return errorResponse(rateLimitError);
    }

    const modelHint = new URL(req.url).searchParams.get("model") ?? undefined;
    const { model, modelId } = await resolveProvider(user?.id ?? "anon", modelHint);

    return await withRequestSpan(
      "agent.memoryUpdate",
      {
        identifier_type: user?.id ? "user" : "ip",
        modelId,
        workflow: "memoryUpdate",
      },
      async (): Promise<Response> => {
        const result = await runMemoryAgent({ identifier, model }, body);
        return Promise.resolve(
          result.toUIMessageStreamResponse({
            onError: createErrorHandler(),
          })
        );
      }
    );
  } catch (err) {
    return errorResponse({
      err,
      error: "internal",
      reason: "Internal server error",
      status: 500,
    });
  }
}
