/**
 * @fileoverview Pure handler for chat streaming. SSR wiring lives in the route adapter.
 *
 * The handler composes validation, memory hydration, token clamping, and AI SDK
 * streaming. It is fully dependency-injected to ensure deterministic tests.
 */

import type { LanguageModel, UIMessage } from "ai";
import { convertToModelMessages, streamText as defaultStreamText } from "ai";
import { extractTexts, validateImageAttachments } from "@/app/api/_helpers/attachments";
import { secureUuid } from "@/lib/security/random";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { insertSingle } from "@/lib/supabase/typed-helpers";
import {
  type ChatMessage as ClampMsg,
  clampMaxTokens,
  countTokens,
} from "@/lib/tokens/budget";
import { getModelContextLimit } from "@/lib/tokens/limits";

/**
 * Type representing a resolved AI provider configuration.
 *
 * @property provider - The AI provider name (e.g., 'openai', 'anthropic').
 * @property modelId - The specific model identifier (e.g., 'gpt-4o-mini').
 * @property model - The AI SDK LanguageModel instance.
 */
export type ProviderResolution = {
  provider: string;
  modelId: string;
  model: LanguageModel;
};

/**
 * Function type for resolving AI provider configurations.
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
 * Function type for rate limiting requests.
 *
 * @param identifier - The identifier for the chat.
 * @returns Promise resolving to a dict with success, limit, remaining, and reset.
 */
export type RateLimiter = (identifier: string) => Promise<{
  success: boolean;
  limit?: number;
  remaining?: number;
  reset?: number;
}>;

/**
 * Interface defining dependencies required for chat stream handling.
 *
 * @param supabase - The Supabase client.
 * @param resolveProvider - The function to resolve an AI provider configuration.
 * @param limit - The function to limit the chat.
 * @param logger - The logger.
 * @param clock - The clock.
 * @param config - The configuration.
 * @param stream - The function to stream the chat.
 */
export interface ChatDeps {
  supabase: TypedServerSupabase;
  resolveProvider: ProviderResolver;
  limit?: RateLimiter;
  logger?: {
    info: (msg: string, meta?: Record<string, unknown>) => void;
    error: (msg: string, meta?: Record<string, unknown>) => void;
  };
  clock?: { now: () => number };
  config?: { defaultMaxTokens?: number };
  stream?: typeof defaultStreamText;
}

/**
 * Type representing the payload for chat streaming.
 *
 * @param messages - The messages.
 * @param sessionId - The session ID.
 * @param model - The model.
 * @param desiredMaxTokens - The desired maximum tokens.
 * @param ip - The IP address.
 */
export interface ChatPayload {
  messages?: UIMessage[];
  sessionId?: string;
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
      headers: { "content-type": "application/json" },
      status: 401,
    });
  }

  const messages = Array.isArray(payload.messages) ? payload.messages : [];

  // Rate limit
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

  // Validate attachments
  const att = validateImageAttachments(messages);
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

  // Memory hydration: prepend system prompt with a short memory summary if present
  let systemPrompt = "You are a helpful travel planning assistant.";
  try {
    const { data: memRows } = await deps.supabase
      .from("memories")
      .select("content")
      .eq("user_id", user.id)
      .order("created_at", { ascending: false })
      .limit(3);
    if (Array.isArray(memRows) && memRows.length > 0) {
      const summary = memRows
        .map((r: { content: unknown }) => String(r.content))
        .join("\n");
      systemPrompt += `\n\nUser memory (summary):\n${summary}`;
    }
  } catch {
    // ignore
  }

  // Tokens clamp
  const desired = Number.isFinite(payload.desiredMaxTokens)
    ? Math.max(1, Math.floor(payload.desiredMaxTokens ?? 0))
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

  // Stream via AI SDK (DI allows tests to inject a finite stream stub)
  const stream = deps.stream ?? defaultStreamText;
  const result = stream({
    maxOutputTokens: maxTokens,
    messages: convertToModelMessages(messages),
    model: provider.model,
    system: systemPrompt,
  });

  const reqId = secureUuid();
  deps.logger?.info?.("chat_stream:start", {
    model: provider.modelId,
    requestId: reqId,
    userId: user.id,
  });

  const sessionId = payload.sessionId;

  return result.toUIMessageStreamResponse({
    messageMetadata: async ({ part }) => {
      if (part.type === "start") {
        // Provide a resumable id to help clients reattach to ongoing streams.
        return {
          model: provider.modelId,
          provider: provider.provider,
          reasons,
          requestId: reqId,
          // `resumableId` duplicates `requestId` but is specifically used by the AI SDK client
          // for reconnection attempts, while `requestId` is for logging/tracing.
          resumableId: reqId,
        } as const;
      }
      if (part.type === "finish") {
        const meta = {
          durationMs: (deps.clock?.now?.() ?? Date.now()) - startedAt,
          inputTokens: part.totalUsage?.inputTokens ?? undefined,
          model: provider.modelId,
          outputTokens: part.totalUsage?.outputTokens ?? undefined,
          provider: provider.provider,
          requestId: reqId,
          totalTokens: part.totalUsage?.totalTokens ?? undefined,
        } as const;
        deps.logger?.info?.("chat_stream:finish", meta);
        if (sessionId) {
          try {
            await insertSingle(deps.supabase, "chat_messages", {
              content: "(streamed)",
              metadata: meta,
              role: "assistant",
              // biome-ignore lint/style/useNamingConvention: Database field name
              session_id: sessionId,
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
        message: String((err as { message?: unknown })?.message || err),
        requestId: reqId,
      });
      return "An error occurred while processing your request.";
    },
    originalMessages: messages,
  });
}
