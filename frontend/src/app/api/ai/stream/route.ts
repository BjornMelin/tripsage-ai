/**
 * @fileoverview Demo streaming route using AI SDK v6. Returns a UI Message Stream
 * suitable for AI Elements and AI SDK UI readers.
 */

import { openai } from "@ai-sdk/openai";
import { streamText } from "ai";
import type { NextRequest } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { parseJsonBody } from "@/lib/next/route-helpers";
import {
  type ChatMessage,
  clampMaxTokens,
  countPromptTokens,
} from "../../../../lib/tokens/budget";
import { getModelContextLimit } from "../../../../lib/tokens/limits";

// Allow streaming responses up to 30 seconds
/** Maximum duration (seconds) to allow for streaming responses. */
export const maxDuration = 30;

/**
 * Handle POST requests by streaming a simple demo message via AI SDK.
 *
 * @param req - Next.js request object
 * @param routeContext - Route context from withApiGuards
 * @returns A Response implementing the UI message stream protocol (SSE).
 */
export const POST = withApiGuards({
  auth: false,
  rateLimit: "ai:stream",
  telemetry: "ai.stream",
})(async (req: NextRequest): Promise<Response> => {
  let prompt = "Hello from AI SDK v6";
  let model = "gpt-4o";
  let desiredMaxTokens = 512;
  let messages: ChatMessage[] | undefined;

  // If JSON parsing fails, use default values
  const parsed = await parseJsonBody(req);
  if (!("error" in parsed)) {
    const body = parsed.body as {
      prompt?: string;
      model?: string;
      desiredMaxTokens?: number;
      messages?: ChatMessage[];
    };
    prompt = body.prompt || prompt;
    model = body.model || model;
    if (typeof body.desiredMaxTokens === "number") {
      desiredMaxTokens = body.desiredMaxTokens;
    }
    if (Array.isArray(body.messages)) {
      messages = body.messages;
    }
  }

  // Build message list if not provided
  const finalMessages: ChatMessage[] = messages ?? [{ content: prompt, role: "user" }];

  const { maxTokens, reasons } = clampMaxTokens(finalMessages, desiredMaxTokens, model);

  // If prompt already exhausts the model context window, return a 400 with reasons
  const modelLimit = getModelContextLimit(model);
  const promptTokens = countPromptTokens(finalMessages, model);
  if (modelLimit - promptTokens <= 0) {
    return new Response(
      JSON.stringify({
        error: "No output tokens available for the given prompt and model.",
        model,
        modelContextLimit: modelLimit,
        promptTokens: promptTokens,
        reasons,
      }),
      { headers: { "content-type": "application/json" }, status: 400 }
    );
  }

  const result = await streamText({
    model: openai(model),
    // Prefer messages when available; otherwise prompt.
    ...(messages ? { messages: finalMessages } : { prompt }),
    maxOutputTokens: maxTokens,
  });

  // Return a UI Message Stream response suitable for AI Elements consumers
  return result.toUIMessageStreamResponse();
});
