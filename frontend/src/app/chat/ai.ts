"use server";

import "server-only";

/**
 * @fileoverview Server-side chat action using AI SDK v6 streamText with Supabase auth and Zod validation.
 */

import { resolveProvider } from "@ai/models/registry";
import type { LanguageModel, UIMessage } from "ai";
import { convertToModelMessages, streamText } from "ai";
import { z } from "zod";
import { secureUuid } from "@/lib/security/random";
import { createServerSupabase } from "@/lib/supabase/server";
import { withTelemetrySpan } from "@/lib/telemetry/span";

const chatInputSchema = z.strictObject({
  messages: z.array(z.unknown()).default([]),
  metadata: z.record(z.string(), z.unknown()).optional(),
  text: z.string().trim().min(1, { error: "Message is required" }).max(2000),
});

interface ChatInput {
  text: string;
  messages: UIMessage[];
  metadata?: Record<string, unknown>;
}

const guardModel = (model: unknown): LanguageModel => {
  if (!model || (typeof model !== "function" && typeof model !== "object")) {
    throw new Error("Invalid language model");
  }
  return model as LanguageModel;
};

/**
 * Server action that validates input, enforces auth, and streams an assistant reply.
 */
// biome-ignore lint/suspicious/useAwait: Returns withTelemetrySpan promise which is async
export async function submitChatMessage(input: ChatInput) {
  const parsed = chatInputSchema.parse(input);

  return withTelemetrySpan(
    "chat.rsc.send",
    { attributes: { feature: "chat", route: "/chat" } },
    async () => {
      const supabase = await createServerSupabase();
      const { data } = await supabase.auth.getUser();
      if (!data || !data.user || !data.user.id) {
        const authError = new Error("Unauthorized");
        (authError as Error & { status?: number }).status = 401;
        throw authError;
      }

      const userMessage: UIMessage = {
        id: secureUuid(),
        metadata: parsed.metadata,
        parts: [{ text: parsed.text, type: "text" }],
        role: "user",
      };

      // Cast is safe: messages come from client UIMessage[] state
      const history: UIMessage[] = [...(input.messages as UIMessage[]), userMessage];
      const provider = await resolveProvider(data.user.id, undefined);

      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 30_000);

      let buffer = "";
      try {
        const { textStream } = await streamText({
          abortSignal: controller.signal,
          messages: convertToModelMessages(history),
          model: guardModel(provider.model),
          system:
            "You are TripSage, a concise travel planner. Prefer factual, actionable suggestions.",
        });

        const MaxBufferChars = 16_000;
        for await (const delta of textStream) {
          buffer += delta;
          if (buffer.length > MaxBufferChars) {
            throw new Error("Response too large");
          }
        }
      } catch (error) {
        const reason =
          error instanceof Error && error.name === "AbortError"
            ? "Timed out"
            : error instanceof Error
              ? error.message
              : "Unknown error";
        throw new Error(`Chat generation failed: ${reason}`);
      } finally {
        clearTimeout(timeout);
      }

      const assistantMessage: UIMessage = {
        id: secureUuid(),
        metadata: parsed.metadata,
        parts: [{ text: buffer, type: "text" }],
        role: "assistant",
      };

      return {
        assistantMessage,
        userMessage,
      };
    }
  );
}
