/**
 * @fileoverview Pure handler for non-streaming chat responses. SSR wiring lives
 * in the route adapter. Mirrors streaming handler semantics: auth, attachments
 * validation, provider resolution, token clamping, and usage metadata.
 */

import type { ProviderResolution } from "@ai/models/registry";
import type { ToolSet, UIMessage } from "ai";
import { convertToModelMessages, generateText as defaultGenerateText } from "ai";
import { extractTexts, validateImageAttachments } from "@/app/api/_helpers/attachments";
import { handleMemoryIntent } from "@/lib/memory/orchestrator";
import {
  createTextMemoryTurn,
  persistMemoryTurn,
  uiMessageToMemoryTurn,
} from "@/lib/memory/turn-utils";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { insertSingle } from "@/lib/supabase/typed-helpers";
import {
  type ChatMessage as ClampMsg,
  clampMaxTokens,
  countTokens,
} from "@/lib/tokens/budget";
import { getModelContextLimit } from "@/lib/tokens/limits";

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
    info: (msg: string, meta?: Record<string, unknown>) => void;
    error: (msg: string, meta?: Record<string, unknown>) => void;
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
 * @param sessionId - The session ID.
 * @param model - The model.
 * @param desiredMaxTokens - The desired maximum tokens.
 * @param ip - The IP address.
 */
export interface NonStreamPayload {
  messages?: UIMessage[];
  sessionId?: string;
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
  const sessionId = payload.sessionId?.trim() || null;

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

  // Memory hydration (best-effort via orchestrator)
  let systemPrompt = "You are a helpful travel planning assistant.";
  try {
    const sessionIdForFetch = sessionId ?? "";
    const memoryResult = await handleMemoryIntent({
      limit: 3,
      sessionId: sessionIdForFetch,
      type: "fetchContext",
      userId: user.id,
    });

    const items = memoryResult.context ?? [];
    if (items.length > 0) {
      const summary = items.map((item) => item.context).join("\n");
      systemPrompt += `\n\nUser memory (summary):\n${summary}`;
    }
  } catch (error) {
    deps.logger?.error?.("chat_non_stream:memory_fetch_failed", {
      error: error instanceof Error ? error.message : String(error),
      sessionId: payload.sessionId,
      userId: user.id,
    });
    // Memory enrichment is best-effort; ignore orchestrator failures
  }

  // Token clamp
  const desired = Number.isFinite(payload.desiredMaxTokens as number)
    ? Math.max(1, Math.floor(payload.desiredMaxTokens as number))
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
  const tools = await (async (): Promise<Record<string, unknown>> => {
    // Import tools from the centralized registry
    let local: Record<string, unknown> = {};
    try {
      const toolsModule = await import("@ai/tools");
      local = {
        createTravelPlan: toolsModule.createTravelPlan,
        deleteTravelPlan: toolsModule.deleteTravelPlan,
        saveTravelPlan: toolsModule.saveTravelPlan,
        updateTravelPlan: toolsModule.updateTravelPlan,
      } as Record<string, unknown>;
    } catch {
      // If tools cannot be imported (e.g., AI SDK mocked without `tool`), proceed without tools.
      local = {};
    }
    const wrapWithUser = (t: unknown) =>
      typeof (t as { execute?: unknown })?.execute === "function"
        ? {
            ...(t as Record<string, unknown>),
            execute: (a: Record<string, unknown>, c: unknown) =>
              (t as { execute: (x: unknown, y?: unknown) => Promise<unknown> }).execute(
                { ...a, userId: user.id },
                c
              ),
          }
        : t;
    if (local.createTravelPlan)
      local.createTravelPlan = wrapWithUser(local.createTravelPlan);
    if (local.updateTravelPlan)
      local.updateTravelPlan = wrapWithUser(local.updateTravelPlan);
    if (local.saveTravelPlan) local.saveTravelPlan = wrapWithUser(local.saveTravelPlan);
    if (local.deleteTravelPlan)
      local.deleteTravelPlan = wrapWithUser(local.deleteTravelPlan);
    return local as unknown as Record<string, unknown>;
  })();

  if (sessionId) {
    const latestMessage =
      messages.length > 0 ? messages[messages.length - 1] : undefined;
    await persistMemoryTurn({
      logger: deps.logger,
      sessionId,
      turn: latestMessage ? uiMessageToMemoryTurn(latestMessage) : null,
      userId: user.id,
    });
  }

  const result = await generate({
    maxOutputTokens: maxTokens,
    messages: convertToModelMessages(messages),
    model: provider.model,
    system: systemPrompt,
    toolChoice: "auto",
    tools: tools as ToolSet,
  });

  const usage = result.usage
    ? {
        completionTokens: result.usage.outputTokens || 0,
        promptTokens: result.usage.inputTokens || 0,
        totalTokens: result.usage.totalTokens || 0,
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
  await persistMemoryTurn({
    logger: deps.logger,
    sessionId,
    turn: createTextMemoryTurn("assistant", result.text ?? ""),
    userId: user.id,
  });

  if (sessionId) {
    try {
      await insertSingle(deps.supabase, "chat_messages", {
        content: result.text ?? "",
        metadata: body,
        role: "assistant",
        // biome-ignore lint/style/useNamingConvention: Database field name
        session_id: sessionId,
      });
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
