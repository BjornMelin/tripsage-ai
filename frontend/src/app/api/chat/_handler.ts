/**
 * @fileoverview Pure handler for non-streaming chat responses. SSR wiring lives
 * in the route adapter. Mirrors streaming handler semantics: auth, attachments
 * validation, provider resolution, token clamping, and usage metadata.
 */

import type { LanguageModel, UIMessage } from "ai";
import { convertToModelMessages, generateText as defaultGenerateText } from "ai";
import { extractTexts, validateImageAttachments } from "@/app/api/_helpers/attachments";
import type { ChatMessageInsert } from "@/lib/supabase/database.types";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import {
  type ChatMessage as ClampMsg,
  clampMaxTokens,
  countTokens,
} from "@/lib/tokens/budget";
import { getModelContextLimit } from "@/lib/tokens/limits";

/**
 * Type representing a resolved AI provider configuration.
 *
 * @param provider - The provider.
 * @param modelId - The model ID.
 * @param model - The model.
 */
export type ProviderResolution = {
  provider: string;
  modelId: string;
  model: LanguageModel;
};

/**
 * Type representing a function that resolves an AI provider configuration.
 *
 * @param userId - The user ID for the chat.
 * @param modelHint - An optional model hint to resolve.
 * @returns Promise resolving to a ProviderResolution.
 */
export type ProviderResolver = (
  userId: string,
  modelHint?: string
) => Promise<ProviderResolution>;

/**
 * Type representing the dependencies for non-streaming chat handling.
 *
 * @param supabase - The Supabase client.
 * @param resolveProvider - The function to resolve an AI provider configuration.
 * @param logger - The logger.
 * @param clock - The clock.
 * @param config - The configuration.
 * @param generate - The function to generate text.
 * @param limit - The function to limit the chat.
 */
export interface NonStreamDeps {
  supabase: TypedServerSupabase;
  resolveProvider: ProviderResolver;
  logger?: {
    info: (msg: string, meta?: any) => void;
    error: (msg: string, meta?: any) => void;
  };
  clock?: { now: () => number };
  config?: { defaultMaxTokens?: number };
  generate?: typeof defaultGenerateText;
  limit?: (identifier: string) => Promise<{
    success: boolean;
    limit?: number;
    remaining?: number;
    reset?: number;
  }>;
}

/**
 * Type representing the payload for non-streaming chat handling.
 *
 * @param messages - The messages.
 * @param session_id - The session ID.
 * @param model - The model.
 * @param desiredMaxTokens - The desired maximum tokens.
 * @param ip - The IP address.
 */
export interface NonStreamPayload {
  messages?: UIMessage[];
  session_id?: string;
  model?: string;
  desiredMaxTokens?: number;
  ip?: string;
}

/**
 * Handle non-streaming chat completion with dependency injection for tests.
 * Returns JSON with content, model, and optional usage.
 *
 * @param deps - Dependencies required for chat handling.
 * @param payload - Chat request payload containing messages and configuration.
 * @returns Promise resolving to a Response with chat completion data.
 */
export async function handleChatNonStream(
  deps: NonStreamDeps,
  payload: NonStreamPayload
): Promise<Response> {
  const startedAt = deps.clock?.now?.() ?? Date.now();

  // SSR auth
  const { data: auth } = await deps.supabase.auth.getUser();
  const user = auth?.user ?? null;
  if (!user) {
    return new Response(JSON.stringify({ error: "unauthorized" }), {
      headers: { "content-type": "application/json" },
      status: 401,
    });
  }

  const messages = Array.isArray(payload.messages) ? payload.messages : [];

  // Optional rate limit
  if (deps.limit) {
    const identifier = `${user.id}:${payload.ip ?? "unknown"}`;
    const { success } = await deps.limit(identifier);
    if (!success) {
      return new Response(JSON.stringify({ error: "rate_limited" }), {
        headers: { "content-type": "application/json", "Retry-After": "60" },
        status: 429,
      });
    }
  }

  // Validate attachments (image/* only)
  const att = validateImageAttachments(messages as any);
  if (!att.valid) {
    return new Response(
      JSON.stringify({ error: "invalid_attachment", reason: att.reason }),
      { headers: { "content-type": "application/json" }, status: 400 }
    );
  }

  // Provider resolution
  const provider = await deps.resolveProvider(
    user.id,
    (payload.model || "").trim() || undefined
  );

  // Memory hydration (best-effort)
  let systemPrompt = "You are a helpful travel planning assistant.";
  try {
    const { data: memRows } = await deps.supabase
      .from("memories")
      .select("content")
      .eq("user_id", user.id)
      .order("created_at", { ascending: false })
      .limit(3);
    if (Array.isArray(memRows) && memRows.length > 0) {
      const summary = memRows.map((r: any) => String(r.content)).join("\n");
      systemPrompt += `\n\nUser memory (summary):\n${summary}`;
    }
  } catch {
    // ignore
  }

  // Token clamp
  const desired = Number.isFinite(payload.desiredMaxTokens as number)
    ? Math.max(1, Math.floor(payload.desiredMaxTokens!))
    : (deps.config?.defaultMaxTokens ?? 1024);

  const textParts = extractTexts(messages);
  const promptCount = countTokens([systemPrompt, ...textParts], provider.modelId);
  const modelLimit = getModelContextLimit(provider.modelId);
  const available = Math.max(0, modelLimit - promptCount);
  if (available <= 0) {
    return new Response(
      JSON.stringify({
        error: "No output tokens available",
        reasons: ["maxTokens_clamped_model_limit"],
      }),
      { headers: { "content-type": "application/json" }, status: 400 }
    );
  }
  const clampInput: ClampMsg[] = [
    { content: systemPrompt, role: "system" },
    { content: textParts.join(" "), role: "user" },
  ];
  const { maxTokens, reasons } = clampMaxTokens(clampInput, desired, provider.modelId);

  const generate = deps.generate ?? defaultGenerateText;
  const result = await generate({
    maxOutputTokens: maxTokens,
    messages: convertToModelMessages(messages as any),
    model: provider.model,
    system: systemPrompt,
  });

  const usage = result.usage
    ? {
        completionTokens: (result.usage as any).completionTokens,
        promptTokens: (result.usage as any).promptTokens,
        totalTokens: result.usage.totalTokens,
      }
    : undefined;

  const body = {
    content: result.text ?? "",
    durationMs: (deps.clock?.now?.() ?? Date.now()) - startedAt,
    model: provider.modelId,
    reasons,
    usage,
  } as const;

  // Best-effort persistence for assistant message metadata
  const sessionId = payload.session_id;
  if (sessionId) {
    try {
      await (deps.supabase as unknown as any).from("chat_messages").insert({
        content: result.text ?? "",
        metadata: body as any,
        role: "assistant",
        session_id: sessionId,
      } as ChatMessageInsert);
    } catch {
      // ignore persistence errors
    }
  }

  deps.logger?.info?.("chat_non_stream:finish", {
    durationMs: body.durationMs,
    model: provider.modelId,
    userId: user.id,
  });

  return new Response(JSON.stringify(body), {
    headers: { "content-type": "application/json" },
    status: 200,
  });
}
