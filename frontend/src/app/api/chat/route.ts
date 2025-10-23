import { convertToModelMessages, streamText } from "ai";
import { openai } from "@ai-sdk/openai";
import type { NextRequest } from "next/server";

/**
 * Native AI SDK v5 route: streams UIMessage responses.
 * Expects AI SDK client to POST { messages: UIMessage[] }.
 */
export async function POST(req: NextRequest) {
  const { messages } = await req.json();
  const model = openai(process.env.OPENAI_MODEL || "gpt-4o-mini");

  const result = streamText({
    model,
    messages: convertToModelMessages(messages || []),
  });

  return result.toUIMessageStreamResponse({
    originalMessages: messages || [],
    generateMessageId: () => crypto.randomUUID(),
    onError: () => ({ errorCode: "STREAM_ERROR", message: "Chat streaming failed" }),
  });
}
