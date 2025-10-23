import { openai } from "@ai-sdk/openai";
import { convertToModelMessages, streamText, tool } from "ai";
import type { NextRequest } from "next/server";
import { z } from "zod";

/**
 * Native AI SDK v5 route: streams UIMessage responses.
 * Expects AI SDK client to POST { messages: UIMessage[] }.
 */
export async function POST(req: NextRequest) {
  const { messages } = await req.json();
  const model = openai(process.env.OPENAI_MODEL || "gpt-4o-mini");

  const tools = {
    confirm: tool({
      description: "Ask the user to confirm an action with an optional note.",
      inputSchema: z.object({ ok: z.boolean(), note: z.string().optional() }),
      async execute({ ok, note }) {
        return { status: ok ? "confirmed" : "cancelled", note: note ?? "" };
      },
    }),
  };

  const result = streamText({
    model,
    messages: convertToModelMessages(messages || []),
    tools,
  });

  return result.toUIMessageStreamResponse({
    originalMessages: messages || [],
    generateMessageId: () => crypto.randomUUID(),
    onError: (error: unknown) => {
      if (typeof error === "string") return error;
      if (error && typeof (error as any).message === "string")
        return (error as any).message;
      return "Chat streaming failed";
    },
  });
}
