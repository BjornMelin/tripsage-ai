/**
 * @fileoverview Demo streaming route using AI SDK v6. Returns a UI Message Stream
 * suitable for AI Elements and AI SDK UI readers.
 */
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
export async function POST(_req?: Request): Promise<Response> {
  const result = streamText({
    // Using a placeholder provider/model id; no secrets required for this demo route
    model: "openai/gpt-4o",
    prompt: "Hello from AI SDK v6",
  });

  // Return a UI Message Stream response suitable for AI Elements consumers
  return result.toUIMessageStreamResponse();
}
