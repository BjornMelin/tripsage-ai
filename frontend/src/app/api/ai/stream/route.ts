/**
 * @fileoverview Demo streaming route using AI SDK v6. Returns a UI Message Stream
 * suitable for AI Elements and AI SDK UI readers.
 */

import { openai } from "@ai-sdk/openai";
import { streamText } from "ai";

// Allow streaming responses up to 30 seconds
/** Maximum duration (seconds) to allow for streaming responses. */
export const maxDuration = 30;

/**
 * Handle POST requests by streaming a simple demo message via AI SDK.
 *
 * @param _req Incoming Request (unused for demo; reserved for future prompt input).
 * @returns A Response implementing the UI message stream protocol (SSE).
 */
export async function POST(req: Request): Promise<Response> {
  let prompt = "Hello from AI SDK v6";

  try {
    const body = (await req.json()) as { prompt?: string };
    prompt = body.prompt || prompt;
  } catch (error) {
    // If JSON parsing fails, use default prompt
    console.warn("Failed to parse request body, using default prompt:", error);
  }

  const result = await streamText({
    model: openai("gpt-4o"),
    prompt,
  });

  // Return a UI Message Stream response suitable for AI Elements consumers
  return result.toUIMessageStreamResponse();
}
