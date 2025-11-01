/**
 * @fileoverview Next.js route handler that streams chat completions using AI SDK v6.
 * Returns a DataStream (SSE) compatible with `@ai-sdk/react` useChat transport.
 */

import { openai } from "@ai-sdk/openai";
import { convertToModelMessages, streamText, type UIMessage } from "ai";

// Allow streaming responses for up to 60 seconds
export const maxDuration = 60;

/**
 * POST /api/chat/stream
 *
 * Expects a JSON payload: { messages: UIMessage[] }
 * Streams text deltas (DataStream) suitable for `useChat`.
 */
export async function POST(req: Request): Promise<Response> {
  const { messages = [] }: { messages?: UIMessage[] } = await req
    .json()
    .catch(() => ({ messages: [] }));

  const result = streamText({
    model: openai("gpt-4o"),
    messages: convertToModelMessages(messages),
    system: "You are a helpful travel planning assistant.",
  });

  // Return a UI Message Stream response suitable for AI Elements consumers
  return result.toUIMessageStreamResponse();
}
