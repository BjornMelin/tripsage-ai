/**
 * @fileoverview Demo streaming route using AI SDK v6. Returns a UI Message Stream suitable for AI Elements and AI SDK UI readers.
 */

import "server-only";

import { resolveProvider } from "@ai/models/registry";
import { buildTimeoutConfigFromSeconds } from "@ai/timeout";
import { consumeStream, streamText } from "ai";
import type { NextRequest } from "next/server";
import { z } from "zod";
import { type RouteParamsContext, withApiGuards } from "@/lib/api/factory";
import { errorResponse, requireUserId } from "@/lib/api/route-helpers";
import { getServerEnvVarWithFallback } from "@/lib/env/server";
import {
  type ChatMessage,
  clampMaxTokens,
  countPromptTokens,
} from "@/lib/tokens/budget";
import { getModelContextLimit } from "@/lib/tokens/limits";

const STREAM_BODY_SCHEMA = z.strictObject({
  desiredMaxTokens: z.number().int().min(1).max(4096).default(512),
  messages: z
    .array(
      z.strictObject({
        content: z.string().max(2000),
        role: z.enum(["assistant", "system", "user"]),
      })
    )
    .max(16)
    .default([]),
  model: z.string().trim().min(1).max(200).optional(),
  prompt: z
    .string()
    .max(4000)
    .default("Hello from AI SDK v6")
    .transform((value) => (value.length ? value : "Hello from AI SDK v6")),
});

// Allow streaming responses up to 30 seconds
/** Maximum duration (seconds) to allow for streaming responses. */
export const maxDuration = 30;
const STREAM_TIMEOUT_SECONDS = Math.max(5, maxDuration - 5);

/**
 * Handle POST requests by streaming a simple demo message via AI SDK.
 *
 * @param req - Next.js request object
 * @param routeContext - Route context from withApiGuards
 * @returns A Response implementing the UI message stream protocol (SSE).
 */
// auth: true required to identify the user making streaming requests.
// Compare with /api/telemetry/ai-demo which uses internal-key auth for backend telemetry.
const guardedPOST = withApiGuards({
  auth: true,
  botId: true,
  degradedMode: "fail_closed",
  rateLimit: "ai:stream",
  schema: STREAM_BODY_SCHEMA,
  telemetry: "ai.stream",
})(async (req, { user }, body) => {
  const auth = requireUserId(user);
  if (!auth.ok) return auth.error;
  const userId = auth.data;

  const { desiredMaxTokens, model: modelHint, prompt } = body;
  const messages: ChatMessage[] | undefined = body.messages.length
    ? body.messages
    : undefined;

  // Build message list if not provided
  const finalMessages: ChatMessage[] = messages ?? [{ content: prompt, role: "user" }];

  let resolved: Awaited<ReturnType<typeof resolveProvider>>;
  try {
    resolved = await resolveProvider(userId, modelHint);
  } catch (error) {
    return errorResponse({
      err: error instanceof Error ? error : new Error(String(error)),
      error: "provider_unavailable",
      reason: "AI provider is not configured yet.",
      status: 503,
    });
  }

  const { maxOutputTokens, reasons } = clampMaxTokens(
    finalMessages,
    desiredMaxTokens,
    resolved.modelId
  );

  // If prompt already exhausts the model context window, return a 400 with reasons
  const modelLimit = getModelContextLimit(resolved.modelId);
  const promptTokens = countPromptTokens(finalMessages, resolved.modelId);
  if (modelLimit - promptTokens <= 0) {
    return errorResponse({
      error: "token_budget_exceeded",
      extras: {
        modelContextLimit: modelLimit,
        modelHint: modelHint ?? null,
        modelId: resolved.modelId,
        promptTokens,
        provider: resolved.provider,
        reasons,
      },
      reason: "No output tokens available for the given prompt and model.",
      status: 400,
    });
  }

  const result = streamText({
    abortSignal: req.signal,
    experimental_telemetry: {
      functionId: "ai.stream.demo",
      isEnabled: true,
      metadata: {
        hasMessages: Boolean(messages?.length),
        modelId: resolved.modelId,
        provider: resolved.provider,
        ...(typeof modelHint === "string" ? { modelHint } : {}),
      },
    },
    maxOutputTokens,
    messages: finalMessages,
    model: resolved.model,
    timeout: buildTimeoutConfigFromSeconds(STREAM_TIMEOUT_SECONDS),
  });

  // Return a UI Message Stream response suitable for AI Elements consumers
  return result.toUIMessageStreamResponse({ consumeSseStream: consumeStream });
});

/**
 * Feature-flagged POST handler for AI streaming demo.
 *
 * @param req - Next.js request object
 * @param routeContext - Route context with params
 * @returns 404 error response when ENABLE_AI_DEMO is disabled, otherwise delegates to guardedPOST
 */
export const POST = async (req: NextRequest, routeContext: RouteParamsContext) => {
  const enabled = getServerEnvVarWithFallback("ENABLE_AI_DEMO", false);
  if (!enabled) {
    return errorResponse({ error: "not_found", reason: "Not found", status: 404 });
  }

  return await guardedPOST(req, routeContext);
};
