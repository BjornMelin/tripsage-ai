/**
 * @fileoverview Pure handler for chat streaming using AI SDK v6 ToolLoopAgent.
 */

import {
  CHAT_DEFAULT_SYSTEM_PROMPT,
  type ChatAgentConfig,
  createChatAgent,
  validateChatMessages,
} from "@ai/agents";
import type { ProviderResolution } from "@schemas/providers";
import type { UIMessage } from "ai";
import { createAgentUIStreamResponse } from "ai";
import { errorResponse } from "@/lib/api/route-helpers";
import { handleMemoryIntent } from "@/lib/memory/orchestrator";
import {
  assistantResponseToMemoryTurn,
  persistMemoryTurn,
  uiMessageToMemoryTurn,
} from "@/lib/memory/turn-utils";
import { secureUuid } from "@/lib/security/random";
import type { InsertTables, Json } from "@/lib/supabase/database.types";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { insertSingle } from "@/lib/supabase/typed-helpers";

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
 * Interface defining dependencies required for chat stream handling.
 *
 * All dependencies are injected to enable deterministic testing and
 * avoid module-scope state per AGENTS.md requirements.
 */
export interface ChatDeps {
  supabase: TypedServerSupabase;
  resolveProvider: ProviderResolver;
  logger?: {
    info: (msg: string, meta?: Record<string, unknown>) => void;
    error: (msg: string, meta?: Record<string, unknown>) => void;
  };
  clock?: { now: () => number };
  config?: { defaultMaxTokens?: number };
}

/**
 * Type representing the payload for chat streaming.
 */
export interface ChatPayload {
  messages?: UIMessage[];
  sessionId?: string;
  model?: string;
  desiredMaxTokens?: number;
  ip?: string;
  userId?: string;
  abortSignal?: AbortSignal;
}

/**
 * Handles chat streaming requests using AI SDK v6 ToolLoopAgent.
 *
 * This implementation uses createAgentUIStreamResponse for proper agent loop
 * handling with autonomous tool execution. The agent runs until a stop
 * condition is met (default: 10 steps).
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
  const requestId = secureUuid();

  const userId = typeof payload.userId === "string" ? payload.userId.trim() : "";
  if (!userId) {
    return errorResponse({
      error: "validation_error",
      reason: "userId is required",
      status: 400,
    });
  }

  const messages = Array.isArray(payload.messages) ? payload.messages : [];
  const sessionId = payload.sessionId?.trim() || null;

  // Validate attachments
  const validation = validateChatMessages(messages);
  if (!validation.valid) {
    return errorResponse({
      error: validation.error ?? "validation_error",
      reason: validation.reason ?? "Message validation failed",
      status: 400,
    });
  }

  // Provider resolution
  const provider = await deps.resolveProvider(
    userId,
    (payload.model || "").trim() || undefined
  );

  // Memory hydration: fetch context summary for system prompt enrichment
  let memorySummary: string | undefined;
  try {
    const sessionIdForFetch = sessionId ?? "";
    const memoryResult = await handleMemoryIntent({
      limit: 3,
      sessionId: sessionIdForFetch,
      type: "fetchContext",
      userId,
    });

    const items = memoryResult.context ?? [];
    if (items.length > 0) {
      memorySummary = items.map((item) => item.context).join("\n");
    }
  } catch (error) {
    deps.logger?.error?.("chat_stream:memory_fetch_failed", {
      error: error instanceof Error ? error.message : String(error),
      requestId,
      sessionId,
      userId,
    });
    // Memory enrichment is best-effort; ignore orchestrator failures
  }

  // Persist user message to memory
  if (sessionId) {
    const latestMessage =
      messages.length > 0 ? messages[messages.length - 1] : undefined;
    await persistMemoryTurn({
      logger: deps.logger,
      sessionId,
      turn: latestMessage ? uiMessageToMemoryTurn(latestMessage) : null,
      userId,
    });
  }

  // Configure the chat agent
  const chatConfig = {
    desiredMaxTokens:
      Number.isFinite(payload.desiredMaxTokens) && (payload.desiredMaxTokens ?? 0) > 0
        ? Math.floor(payload.desiredMaxTokens as number)
        : (deps.config?.defaultMaxTokens ?? 1024),
    maxSteps: 10,
    memorySummary,
    systemPrompt: CHAT_DEFAULT_SYSTEM_PROMPT,
    useCallOptions: false,
  } satisfies ChatAgentConfig & { useCallOptions?: false };

  deps.logger?.info?.("chat_stream:start", {
    model: provider.modelId,
    requestId,
    userId,
  });

  // Create the chat agent using ToolLoopAgent
  const { agent, modelId } = createChatAgent(
    {
      identifier: `${userId}:${payload.ip ?? "unknown"}`,
      model: provider.model,
      modelId: provider.modelId,
      sessionId: sessionId ?? undefined,
      userId,
    },
    messages,
    chatConfig
  );

  // Use createAgentUIStreamResponse for proper agent loop handling
  const response = await createAgentUIStreamResponse({
    abortSignal: payload.abortSignal,
    agent,

    // Handle errors during streaming
    onError: (err) => {
      deps.logger?.error?.("chat_stream:error", {
        message: String((err as { message?: unknown })?.message || err),
        requestId,
      });
      return "An error occurred while processing your request.";
    },

    // Handle stream completion for memory persistence and logging
    onFinish: async (event) => {
      const meta: Json = {
        durationMs: (deps.clock?.now?.() ?? Date.now()) - startedAt,
        finishReason: event.finishReason ?? null,
        isContinuation: event.isContinuation,
        model: modelId,
        provider: provider.provider,
        requestId,
      } as const;

      deps.logger?.info?.("chat_stream:finish", meta);

      // Persist assistant response to memory
      if (sessionId && event.messages) {
        try {
          await persistMemoryTurn({
            logger: deps.logger,
            sessionId,
            turn: assistantResponseToMemoryTurn(event.messages),
            userId,
          });

          const chatMessagePayload: InsertTables<"chat_messages"> & {
            // Some deployments may expose request_id; keep optional to avoid schema breakage
            // biome-ignore lint/style/useNamingConvention: Database field name
            request_id?: string | null;
          } = {
            content: "(streamed)",
            metadata: meta,
            role: "assistant",
            // biome-ignore lint/style/useNamingConvention: Database field name
            session_id: sessionId,
            // biome-ignore lint/style/useNamingConvention: Database field name
            user_id: userId,
          };

          // Store requestId at top-level when column exists; otherwise remains in metadata
          chatMessagePayload.request_id = requestId ?? null;

          await insertSingle(deps.supabase, "chat_messages", chatMessagePayload);
        } catch (error) {
          deps.logger?.error?.("chat_stream:memory_response_failed", {
            error: error instanceof Error ? error.message : String(error),
            requestId,
            sessionId,
            userId,
          });
        }
      }
    },
    uiMessages: messages,
  });

  return response;
}
