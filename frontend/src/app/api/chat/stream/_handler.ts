/**
 * @fileoverview Pure handler for chat streaming. SSR wiring lives in the route adapter.
 *
 * The handler composes validation, memory hydration, token clamping, and AI SDK
 * streaming. It is fully dependency-injected to ensure deterministic tests.
 */

import type { SupabaseClient } from "@supabase/supabase-js";
import type { LanguageModel, UIMessage } from "ai";
import { convertToModelMessages, streamText as defaultStreamText } from "ai";
import { extractTexts, validateImageAttachments } from "@/app/api/_helpers/attachments";
import {
  type ChatMessage as ClampMsg,
  clampMaxTokens,
  countTokens,
} from "@/lib/tokens/budget";
import { getModelContextLimit } from "@/lib/tokens/limits";

/**
 * Type representing a resolved AI provider configuration.
 */
export type ProviderResolution = {
  provider: string;
  modelId: string;
  model: LanguageModel;
};

/**
 * Function type for resolving AI provider configurations.
 */
export type ProviderResolver = (
  userId: string,
  modelHint?: string
) => Promise<ProviderResolution>;

/**
 * Function type for rate limiting requests.
 */
export type RateLimiter = (identifier: string) => Promise<{
  success: boolean;
  limit?: number;
  remaining?: number;
  reset?: number;
}>;

/**
 * Interface defining dependencies required for chat stream handling.
 */
export interface ChatDeps {
  supabase: SupabaseClient<any>;
  resolveProvider: ProviderResolver;
  limit?: RateLimiter;
  logger?: {
    info: (msg: string, meta?: any) => void;
    error: (msg: string, meta?: any) => void;
  };
  clock?: { now: () => number };
  config?: { defaultMaxTokens?: number };
  stream?: typeof defaultStreamText;
}

/**
 * Interface defining the payload structure for chat stream requests.
 */
export interface ChatPayload {
  messages?: UIMessage[];
  session_id?: string;
  model?: string;
  desiredMaxTokens?: number;
  ip?: string;
}

/**
 * Handles chat streaming requests with authentication, rate limiting, and AI SDK integration.
 *
 * @param deps - Dependencies required for chat stream handling.
 * @param payload - Chat request payload containing messages and configuration.
 * @returns Promise resolving to a Response with streamed chat data.
 */
/**
 * Handle chat streaming with injected dependencies.
 *
 * @param deps Collaborators: `supabase`, `resolveProvider`, optional `limit`,
 *   `logger`, `clock`, `config`, and optional `stream` factory used by AI SDK.
 * @param payload Request payload from the client (messages, model, desired tokens).
 * @returns A Response suitable for `@ai-sdk/ui` consumption (UIMessageStream).
 */
export async function handleChatStream(
  deps: ChatDeps,
  payload: ChatPayload
): Promise<Response> {
  const startedAt = deps.clock?.now?.() ?? Date.now();

  // SSR auth via injected supabase
  const { data: auth } = await deps.supabase.auth.getUser();
  const user = auth?.user ?? null;
  if (!user) {
    return new Response(JSON.stringify({ error: "unauthorized" }), {
      status: 401,
      headers: { "content-type": "application/json" },
    });
  }

  const messages = Array.isArray(payload.messages) ? payload.messages : [];

  // Rate limit
  if (deps.limit) {
    const identifier = `${user.id}:${payload.ip ?? "unknown"}`;
    const { success } = await deps.limit(identifier);
    if (!success) {
      return new Response(JSON.stringify({ error: "rate_limited" }), {
        status: 429,
        headers: { "Retry-After": "60", "content-type": "application/json" },
      });
    }
  }

  // Validate attachments
  const att = validateImageAttachments(messages);
  if (!att.valid) {
    return new Response(
      JSON.stringify({ error: "invalid_attachment", reason: att.reason }),
      { status: 400, headers: { "content-type": "application/json" } }
    );
  }

  // Provider resolution
  const provider = await deps.resolveProvider(
    user.id,
    (payload.model || "").trim() || undefined
  );

  // Memory hydration: prepend system prompt with a short memory summary if present
  let systemPrompt = "You are a helpful travel planning assistant.";
  try {
    const { data: memRows } = await (deps.supabase as any)
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

  // Tokens clamp
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
      { status: 400, headers: { "content-type": "application/json" } }
    );
  }
  const clampInput: ClampMsg[] = [
    { role: "system", content: systemPrompt },
    { role: "user", content: textParts.join(" ") },
  ];
  const { maxTokens, reasons } = clampMaxTokens(clampInput, desired, provider.modelId);
  if (maxTokens <= 0) {
    return new Response(
      JSON.stringify({ error: "No output tokens available", reasons }),
      { status: 400, headers: { "content-type": "application/json" } }
    );
  }

  // Stream via AI SDK (DI allows tests to inject a finite stream stub)
  const stream = deps.stream ?? defaultStreamText;
  const result = stream({
    model: provider.model,
    system: systemPrompt,
    maxOutputTokens: maxTokens,
    messages: convertToModelMessages(messages),
  });

  const reqId = Math.random().toString(36).slice(2);
  deps.logger?.info?.("chat_stream:start", {
    requestId: reqId,
    userId: user.id,
    model: provider.modelId,
  });

  const sessionId = payload.session_id;

  return result.toUIMessageStreamResponse({
    originalMessages: messages,
    messageMetadata: async ({ part }) => {
      if (part.type === "start") {
        return { requestId: reqId, model: provider.modelId, reasons };
      }
      if (part.type === "finish") {
        const meta = {
          totalTokens: part.totalUsage?.totalTokens ?? undefined,
          inputTokens: part.totalUsage?.inputTokens ?? undefined,
          outputTokens: part.totalUsage?.outputTokens ?? undefined,
          model: provider.modelId,
          requestId: reqId,
          durationMs: (deps.clock?.now?.() ?? Date.now()) - startedAt,
        } as const;
        deps.logger?.info?.("chat_stream:finish", meta);
        if (sessionId) {
          try {
            await (deps.supabase as any).from("chat_messages").insert({
              session_id: sessionId,
              role: "assistant",
              content: "(streamed)",
              metadata: meta as any,
            });
          } catch {
            /* ignore */
          }
        }
        return meta;
      }
      return undefined;
    },
    onError: (err) => {
      deps.logger?.error?.("chat_stream:error", {
        requestId: reqId,
        message: String((err as any)?.message || err),
      });
      return "An error occurred while processing your request.";
    },
  });
}
