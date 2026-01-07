/**
 * @fileoverview Pure handler for chat streaming using AI SDK v6 streamText + bounded tool loop.
 */

import "server-only";

import { CHAT_DEFAULT_SYSTEM_PROMPT } from "@ai/constants";
import { toolRegistry } from "@ai/tools";
import { wrapToolsWithChatId, wrapToolsWithUserId } from "@ai/tools/server/injection";
import type { ProviderResolution } from "@schemas/providers";
import type { ModelMessage, ToolSet, UIMessage } from "ai";
import {
  consumeStream,
  convertToModelMessages,
  safeValidateUIMessages,
  stepCountIs,
  streamText,
} from "ai";
import { z } from "zod";
import { validateImageAttachments } from "@/app/api/_helpers/attachments";
import { errorResponse, notFoundResponse } from "@/lib/api/route-helpers";
import { handleMemoryIntent } from "@/lib/memory/orchestrator";
import {
  createTextMemoryTurn,
  persistMemoryTurn,
  uiMessageToMemoryTurn,
} from "@/lib/memory/turn-utils";
import { sanitizeWithInjectionDetection } from "@/lib/security/prompt-sanitizer";
import { nowIso, secureUuid } from "@/lib/security/random";
import type { Json } from "@/lib/supabase/database.types";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { insertSingle, updateSingle } from "@/lib/supabase/typed-helpers";
import type { ServerLogger } from "@/lib/telemetry/logger";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens, countTokens } from "@/lib/tokens/budget";
import { getModelContextLimit } from "@/lib/tokens/limits";

/**
 * Function type for resolving AI provider configurations.
 *
 * @param userId - The authenticated user ID.
 * @param modelHint - Optional model hint to resolve.
 * @returns Promise resolving to a ProviderResolution.
 */
export type ProviderResolver = (
  userId: string,
  modelHint?: string
) => Promise<ProviderResolution>;

export interface ChatDeps {
  supabase: TypedServerSupabase;
  resolveProvider: ProviderResolver;
  logger?: ServerLogger;
  clock?: { now: () => number };
  config?: {
    defaultMaxTokens?: number;
    maxSteps?: number;
  };
}

export interface ChatPayload {
  messages: UIMessage[];
  trigger?: "submit-message" | "regenerate-message";
  messageId?: string;
  sessionId?: string;
  model?: string;
  desiredMaxTokens?: number;
  ip?: string;
  userId: string;
  abortSignal?: AbortSignal;
}

const toolCallSchema = z.looseObject({
  args: z.unknown().optional(),
  input: z.unknown().optional(),
  toolCallId: z.string(),
  toolName: z.string(),
});

const toolResultSchema = z.looseObject({
  isError: z.boolean().optional(),
  result: z.unknown().optional(),
  toolCallId: z.string(),
  toolName: z.string(),
});

type ParsedToolCall = z.infer<typeof toolCallSchema>;
type ParsedToolResult = z.infer<typeof toolResultSchema>;

function getLastUserText(messages: UIMessage[]): string | undefined {
  const last = messages.findLast((m) => m.role === "user");
  if (!last) return undefined;
  const parts = Array.isArray(last.parts) ? last.parts : [];
  const chunks = parts
    .map((part) => (part?.type === "text" ? part.text : undefined))
    .filter(
      (text): text is string => typeof text === "string" && text.trim().length > 0
    );
  if (chunks.length === 0) return undefined;
  return chunks.join("\n").trim();
}

async function ensureChatSession(options: {
  sessionId?: string | null;
  supabase: TypedServerSupabase;
  userId: string;
}): Promise<
  { ok: true; sessionId: string; created: boolean } | { ok: false; res: Response }
> {
  const { sessionId, supabase, userId } = options;
  const existingId = sessionId?.trim();

  if (existingId) {
    const { data, error } = await supabase
      .from("chat_sessions")
      .select("id")
      .eq("id", existingId)
      .eq("user_id", userId)
      .maybeSingle();
    if (error) {
      return {
        ok: false,
        res: errorResponse({
          err: new Error(error.message),
          error: "db_error",
          reason: "Failed to verify session",
          status: 500,
        }),
      };
    }
    if (!data) {
      return { ok: false, res: notFoundResponse("Session") };
    }
    return { created: false, ok: true, sessionId: existingId };
  }

  const id = secureUuid();
  const now = nowIso();
  const { error } = await insertSingle(supabase, "chat_sessions", {
    // biome-ignore lint/style/useNamingConvention: Database field name
    created_at: now,
    id,
    metadata: {},
    // biome-ignore lint/style/useNamingConvention: Database field name
    updated_at: now,
    // biome-ignore lint/style/useNamingConvention: Database field name
    user_id: userId,
  });

  if (error) {
    return {
      ok: false,
      res: errorResponse({
        err: error instanceof Error ? error : undefined,
        error: "db_error",
        reason: "Failed to create session",
        status: 500,
      }),
    };
  }

  return { created: true, ok: true, sessionId: id };
}

async function persistChatMessage(options: {
  content: string;
  metadata: Json;
  role: "assistant" | "system" | "user";
  sessionId: string;
  supabase: TypedServerSupabase;
  userId: string;
}): Promise<{ ok: true; id: number } | { ok: false; res: Response }> {
  const { content, metadata, role, sessionId, supabase, userId } = options;

  const { data, error } = await insertSingle(supabase, "chat_messages", {
    content,
    metadata,
    role,
    // biome-ignore lint/style/useNamingConvention: Database field name
    session_id: sessionId,
    // biome-ignore lint/style/useNamingConvention: Database field name
    user_id: userId,
  });

  if (error) {
    return {
      ok: false,
      res: errorResponse({
        err: error instanceof Error ? error : undefined,
        error: "db_error",
        reason: "Failed to persist message",
        status: 500,
      }),
    };
  }

  const insertedId = data?.id;
  if (typeof insertedId !== "number") {
    return {
      ok: false,
      res: errorResponse({
        error: "db_error",
        reason: "Failed to resolve persisted message id",
        status: 500,
      }),
    };
  }

  return { id: insertedId, ok: true };
}

function buildSystemPrompt(options: {
  memorySummary?: string;
  systemPrompt?: string;
}): string {
  const systemPrompt = options.systemPrompt ?? CHAT_DEFAULT_SYSTEM_PROMPT;

  const memorySummary = options.memorySummary?.trim();
  if (!memorySummary) return systemPrompt;

  const sanitizedMemory = sanitizeWithInjectionDetection(memorySummary, 2000);
  return `${systemPrompt}\n\n<user_memory role="context">\n${sanitizedMemory}\n</user_memory>`;
}

function extractTokenTextsFromModelMessages(messages: ModelMessage[]): string[] {
  const texts: string[] = [];

  for (const message of messages) {
    const content = message.content;

    if (typeof content === "string") {
      if (content.trim().length > 0) texts.push(content);
      continue;
    }

    if (!Array.isArray(content)) continue;

    for (const part of content) {
      if (!part || typeof part !== "object") continue;

      if (part.type === "text" && typeof part.text === "string") {
        if (part.text.trim().length > 0) texts.push(part.text);
        continue;
      }

      if (part.type === "reasoning" && typeof part.text === "string") {
        if (part.text.trim().length > 0) texts.push(part.text);
        continue;
      }

      // Avoid counting raw file/base64 content; count a lightweight placeholder instead.
      if (
        part.type === "file" &&
        "mediaType" in part &&
        typeof part.mediaType === "string"
      ) {
        texts.push(`[file:${part.mediaType}]`);
        continue;
      }

      // Tool calls/results can carry significant prompt cost; include a compact JSON form.
      if (part.type === "tool-call") {
        const toolName = "toolName" in part ? part.toolName : undefined;
        const input = "input" in part ? part.input : undefined;
        try {
          texts.push(JSON.stringify({ input, toolName }));
        } catch {
          texts.push(String(toolName ?? "tool-call"));
        }
        continue;
      }

      if (part.type === "tool-result") {
        const toolName = "toolName" in part ? part.toolName : undefined;
        const output = "output" in part ? part.output : undefined;
        try {
          texts.push(JSON.stringify({ output, toolName }));
        } catch {
          texts.push(String(toolName ?? "tool-result"));
        }
      }
    }
  }

  return texts;
}

function buildTokenBudget(options: {
  desiredMaxTokens?: number;
  modelId: string;
  modelMessages: ModelMessage[];
  system: string;
}): { ok: true; maxOutputTokens: number } | { ok: false; res: Response } {
  const desired =
    typeof options.desiredMaxTokens === "number" &&
    Number.isFinite(options.desiredMaxTokens) &&
    options.desiredMaxTokens > 0
      ? Math.floor(options.desiredMaxTokens)
      : 1024;

  const tokenTexts = extractTokenTextsFromModelMessages(options.modelMessages);
  const promptCount = countTokens([options.system, ...tokenTexts], options.modelId);
  const modelLimit = getModelContextLimit(options.modelId);
  const available = Math.max(0, modelLimit - promptCount);

  if (available <= 0) {
    return {
      ok: false,
      res: errorResponse({
        error: "token_budget_exceeded",
        extras: {
          modelContextLimit: modelLimit,
          modelId: options.modelId,
          promptTokens: promptCount,
        },
        reason: "No output tokens available for the given prompt and model.",
        status: 400,
      }),
    };
  }

  const clampInput: ChatMessage[] = [
    { content: options.system, role: "system" },
    { content: tokenTexts.join(" "), role: "user" },
  ];
  const { maxTokens } = clampMaxTokens(clampInput, desired, options.modelId);

  return { maxOutputTokens: maxTokens, ok: true };
}

function parseToolCall(value: unknown): ParsedToolCall | null {
  const parsed = toolCallSchema.safeParse(value);
  return parsed.success ? parsed.data : null;
}

function parseToolResult(value: unknown): ParsedToolResult | null {
  const parsed = toolResultSchema.safeParse(value);
  return parsed.success ? parsed.data : null;
}

function encodePartsToContent(parts: UIMessage["parts"] | undefined): string {
  const safeParts = Array.isArray(parts) ? parts : [];
  try {
    return JSON.stringify(safeParts);
  } catch {
    return "[]";
  }
}

function getTextFromUiMessage(message: UIMessage): string {
  const parts = Array.isArray(message.parts) ? message.parts : [];
  const chunks = parts
    .map((part) => (part?.type === "text" ? part.text : undefined))
    .filter((text): text is string => typeof text === "string" && text.length > 0);
  if (chunks.length === 0) return "";
  return chunks.join("").trim();
}

type ChatTrigger = NonNullable<ChatPayload["trigger"]>;

type HydratedChatMessage = {
  dbId: number;
  isSuperseded: boolean;
  metadata?: Json;
  role: "assistant" | "system" | "user";
  uiMessage: UIMessage;
  uiMessageId: string;
};

const HISTORY_LIMIT = 40;

function isJsonObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function getStringFromMetadata(metadata: unknown, key: string): string | undefined {
  if (!isJsonObject(metadata)) return undefined;
  const value = metadata[key];
  return typeof value === "string" && value.trim().length > 0
    ? value.trim()
    : undefined;
}

function getUiMessageIdFromRow(row: { id: number; metadata: unknown }): string {
  const uiMessageId = getStringFromMetadata(row.metadata, "uiMessageId");
  return uiMessageId ?? `db:${row.id}`;
}

function isSupersededMessage(metadata: unknown): boolean {
  const supersededBy = getStringFromMetadata(metadata, "supersededBy");
  if (supersededBy) return true;
  const status = getStringFromMetadata(metadata, "status");
  return status === "superseded";
}

function toStoredParts(options: {
  content: unknown;
  logger?: ServerLogger;
  sessionId: string;
  messageDbId: number;
}): unknown[] {
  const { content, logger, messageDbId, sessionId } = options;
  if (typeof content !== "string") return [];
  const trimmed = content.trim();
  if (!trimmed) return [];

  try {
    const parsed = JSON.parse(trimmed);
    if (Array.isArray(parsed)) return parsed;
    return [{ text: trimmed, type: "text" }];
  } catch (error) {
    logger?.warn?.("chat:stored_parts_parse_failed", {
      contentLength: trimmed.length,
      error: error instanceof Error ? error.message : String(error),
      messageDbId,
      sessionId,
    });
    return [{ text: trimmed, type: "text" }];
  }
}

async function loadChatHistory(options: {
  limit?: number;
  logger?: ServerLogger;
  sessionId: string;
  supabase: TypedServerSupabase;
  userId: string;
}): Promise<
  { ok: true; messages: HydratedChatMessage[] } | { ok: false; res: Response }
> {
  const limit = options.limit ?? HISTORY_LIMIT;

  const { data: rows, error } = await options.supabase
    .from("chat_messages")
    .select("id, role, content, metadata")
    .eq("session_id", options.sessionId)
    .eq("user_id", options.userId)
    .order("id", { ascending: false })
    .limit(limit);

  if (error) {
    return {
      ok: false,
      res: errorResponse({
        err: new Error(error.message),
        error: "db_error",
        reason: "Failed to load chat history",
        status: 500,
      }),
    };
  }

  const ordered = [...(rows ?? [])].filter((row) => typeof row.id === "number");
  ordered.reverse();

  const messageIds = ordered.map((row) => row.id);

  const { data: toolCalls, error: toolError } =
    messageIds.length > 0
      ? await options.supabase
          .from("chat_tool_calls")
          .select(
            "message_id, tool_id, tool_name, arguments, result, status, error_message"
          )
          .in("message_id", messageIds)
          .order("id", { ascending: true })
      : { data: [], error: null };

  if (toolError) {
    return {
      ok: false,
      res: errorResponse({
        err: new Error(toolError.message),
        error: "db_error",
        reason: "Failed to load tool calls",
        status: 500,
      }),
    };
  }

  const toolCallsByMessageId = new Map<number, Array<(typeof toolCalls)[number]>>();
  for (const toolRow of toolCalls ?? []) {
    const messageId = toolRow.message_id;
    if (typeof messageId !== "number") continue;
    const existing = toolCallsByMessageId.get(messageId) ?? [];
    existing.push(toolRow);
    toolCallsByMessageId.set(messageId, existing);
  }

  const rawUiMessages = ordered.map((row) => {
    const baseParts = toStoredParts({
      content: row.content,
      logger: options.logger,
      messageDbId: row.id,
      sessionId: options.sessionId,
    });

    let role: "assistant" | "system" | "user";
    if (row.role === "user" || row.role === "assistant" || row.role === "system") {
      role = row.role;
    } else {
      role = "assistant";
    }

    const uiMessageId = getUiMessageIdFromRow({ id: row.id, metadata: row.metadata });
    const metadata =
      row.metadata && typeof row.metadata === "object" && !Array.isArray(row.metadata)
        ? row.metadata
        : undefined;

    const enrichedParts = [...baseParts];
    const toolRows = toolCallsByMessageId.get(row.id) ?? [];

    if (toolRows.length > 0 && role === "assistant") {
      for (const toolRow of toolRows) {
        const toolName = toolRow.tool_name;
        const toolCallId = toolRow.tool_id;
        if (typeof toolName !== "string" || toolName.trim().length === 0) continue;
        if (typeof toolCallId !== "string" || toolCallId.trim().length === 0) continue;

        const baseToolPart = {
          input: toolRow.arguments ?? {},
          toolCallId,
          type: `tool-${toolName}`,
        } as const;

        if (toolRow.status === "failed") {
          const errorText =
            toolRow.error_message ??
            (typeof toolRow.result === "string" ? toolRow.result : "Tool failed");
          enrichedParts.push({
            ...baseToolPart,
            errorText,
            state: "output-error",
          });
        } else {
          enrichedParts.push({
            ...baseToolPart,
            output: toolRow.result ?? null,
            state: "output-available",
          });
        }
      }
    }

    return {
      id: uiMessageId,
      metadata,
      parts: enrichedParts,
      role,
    };
  });

  if (rawUiMessages.length === 0) {
    return { messages: [], ok: true };
  }

  const validated = await safeValidateUIMessages({ messages: rawUiMessages });
  if (!validated.success) {
    const normalizedError =
      validated.error instanceof Error
        ? validated.error
        : new Error(String(validated.error ?? "Invalid stored messages"));
    options.logger?.error?.("chat:history_validation_failed", {
      error: normalizedError.message,
      sessionId: options.sessionId,
      userId: options.userId,
    });

    return {
      ok: false,
      res: errorResponse({
        err: normalizedError,
        error: "internal",
        reason: "Failed to parse stored messages",
        status: 500,
      }),
    };
  }

  const hydrated: HydratedChatMessage[] = validated.data.map((uiMessage, index) => {
    const row = ordered[index];
    const uiMessageId = uiMessage.id;
    const isSuperseded = isSupersededMessage(row?.metadata);

    let role: "assistant" | "system" | "user";
    if (
      uiMessage.role === "user" ||
      uiMessage.role === "assistant" ||
      uiMessage.role === "system"
    ) {
      role = uiMessage.role;
    } else {
      role = "assistant";
    }

    return {
      dbId: row?.id ?? 0,
      isSuperseded,
      metadata: uiMessage.metadata as Json | undefined,
      role,
      uiMessage,
      uiMessageId,
    };
  });

  return { messages: hydrated.filter((m) => m.dbId !== 0), ok: true };
}

function mergeAssistantMetadata(
  base: Json | undefined,
  patch: Record<string, Json>
): Json {
  const baseRecord =
    base && typeof base === "object" && !Array.isArray(base)
      ? (base as Record<string, Json>)
      : {};
  return { ...baseRecord, ...patch };
}

export async function handleChat(
  deps: ChatDeps,
  payload: ChatPayload
): Promise<Response> {
  const startedAt = deps.clock?.now?.() ?? Date.now();
  const requestId = secureUuid();

  const userId = payload.userId.trim();
  if (!userId) {
    return errorResponse({
      error: "validation_error",
      reason: "userId is required",
      status: 400,
    });
  }

  const sessionIdHint = payload.sessionId?.trim() || null;
  const trigger: ChatTrigger = payload.trigger ?? "submit-message";

  const sessionResult = await ensureChatSession({
    sessionId: sessionIdHint,
    supabase: deps.supabase,
    userId,
  });
  if (!sessionResult.ok) return sessionResult.res;
  const sessionId = sessionResult.sessionId;

  const provider = await deps.resolveProvider(
    userId,
    (payload.model || "").trim() || undefined
  );

  const historyResult = await loadChatHistory({
    limit: HISTORY_LIMIT,
    logger: deps.logger,
    sessionId,
    supabase: deps.supabase,
    userId,
  });
  if (!historyResult.ok) return historyResult.res;

  const visibleHistory = historyResult.messages.filter((m) => !m.isSuperseded);

  let promptUiMessages: UIMessage[];
  let regenerationOf: string | null = null;

  if (trigger === "submit-message") {
    const clientMessages = Array.isArray(payload.messages) ? payload.messages : [];
    const latest = clientMessages.at(-1);
    if (!latest) {
      return errorResponse({
        error: "invalid_request",
        reason: "message is required",
        status: 400,
      });
    }
    if (latest.role !== "user") {
      return errorResponse({
        error: "invalid_request",
        reason: "message must be a user message",
        status: 400,
      });
    }

    promptUiMessages = [...visibleHistory.map((m) => m.uiMessage), latest];

    // Persist latest user message (best-effort).
    await persistMemoryTurn({
      logger: deps.logger,
      sessionId,
      turn: uiMessageToMemoryTurn(latest),
      userId,
    });

    const userPersist = await persistChatMessage({
      content: encodePartsToContent(latest.parts),
      metadata: {
        uiMessageId: latest.id,
      },
      role: "user",
      sessionId,
      supabase: deps.supabase,
      userId,
    });
    if (!userPersist.ok) return userPersist.res;
  } else {
    const requestedMessageId = payload.messageId?.trim() || undefined;
    const targetIndex = requestedMessageId
      ? visibleHistory.findIndex(
          (m) => m.role === "assistant" && m.uiMessageId === requestedMessageId
        )
      : visibleHistory.findLastIndex((m) => m.role === "assistant");

    if (targetIndex < 0) {
      return errorResponse({
        error: "invalid_request",
        reason: "No assistant message available to regenerate",
        status: 400,
      });
    }

    const target = visibleHistory[targetIndex];
    regenerationOf = target.uiMessageId;

    promptUiMessages = visibleHistory.slice(0, targetIndex).map((m) => m.uiMessage);

    const lastPrompt = promptUiMessages.at(-1);
    if (!lastPrompt || lastPrompt.role !== "user") {
      return errorResponse({
        error: "invalid_request",
        reason: "Cannot regenerate without a preceding user message",
        status: 400,
      });
    }
  }

  const attachmentValidation = validateImageAttachments(promptUiMessages);
  if (!attachmentValidation.valid) {
    return errorResponse({
      error: "invalid_attachment",
      reason: attachmentValidation.reason,
      status: 400,
    });
  }

  // Memory hydration: fetch context (semantic when possible).
  let memorySummary: string | undefined;
  try {
    const query = getLastUserText(promptUiMessages);
    const memoryResult = await handleMemoryIntent({
      limit: 3,
      query,
      sessionId,
      type: "fetchContext",
      userId,
    });
    const items = memoryResult.context ?? [];
    if (items.length > 0) {
      memorySummary = items.map((item) => item.context).join("\n");
    }
  } catch (error) {
    deps.logger?.error?.("chat:memory_fetch_failed", {
      error: error instanceof Error ? error.message : String(error),
      requestId,
      sessionId,
      userId,
    });
  }

  const assistantUiMessageId = secureUuid();

  if (trigger === "regenerate-message" && regenerationOf) {
    const target = visibleHistory.find(
      (m) => m.role === "assistant" && m.uiMessageId === regenerationOf
    );

    if (target) {
      const supersededMeta = mergeAssistantMetadata(target.metadata, {
        status: "superseded",
        supersededAt: nowIso(),
        supersededBy: assistantUiMessageId,
      });

      const { error } = await updateSingle(
        deps.supabase,
        "chat_messages",
        { metadata: supersededMeta },
        (qb) => qb.eq("id", target.dbId).eq("user_id", userId)
      );

      if (error) {
        deps.logger?.warn?.("chat:regenerate_supersede_failed", {
          error: error instanceof Error ? error.message : String(error),
          requestId,
          sessionId,
          userId,
        });
      }
    }
  }

  const assistantBaseMetadata: Json = {
    model: provider.modelId,
    provider: provider.provider,
    regenerationOf,
    requestId,
    sessionId,
    startedAt,
    status: "streaming",
    uiMessageId: assistantUiMessageId,
  };

  const assistantPersist = await persistChatMessage({
    content: "[]",
    metadata: assistantBaseMetadata,
    role: "assistant",
    sessionId,
    supabase: deps.supabase,
    userId,
  });
  if (!assistantPersist.ok) return assistantPersist.res;
  const assistantMessageId = assistantPersist.id;

  const system = buildSystemPrompt({ memorySummary });

  const maxSteps = deps.config?.maxSteps ?? 10;

  // Tools that require user scope injection.
  const userScopedTools = [
    "createTravelPlan",
    "updateTravelPlan",
    "saveTravelPlan",
    "deleteTravelPlan",
    "bookAccommodation",
    "trips.savePlace",
    "webSearch",
    "webSearchBatch",
  ];

  const chatScopedTools = ["attachments.list"];

  const baseTools = wrapToolsWithUserId(
    toolRegistry,
    userId,
    userScopedTools,
    sessionId
  ) satisfies ToolSet;

  const chatTools = wrapToolsWithChatId(
    baseTools,
    sessionId,
    chatScopedTools
  ) satisfies ToolSet;

  const modelMessages = await convertToModelMessages(promptUiMessages, {
    ignoreIncompleteToolCalls: true,
    tools: chatTools,
  });

  const tokenBudget = buildTokenBudget({
    desiredMaxTokens:
      typeof payload.desiredMaxTokens === "number"
        ? payload.desiredMaxTokens
        : deps.config?.defaultMaxTokens,
    modelId: provider.modelId,
    modelMessages,
    system,
  });
  if (!tokenBudget.ok) return tokenBudget.res;

  // Track tool calls already persisted to avoid duplicates across steps.
  const persistedToolCallIds = new Set<string>();

  const result = streamText({
    abortSignal: payload.abortSignal,
    maxOutputTokens: tokenBudget.maxOutputTokens,
    messages: modelMessages,
    model: provider.model,
    onFinish: async ({ finishReason, text, totalUsage }) => {
      const durationMs = (deps.clock?.now?.() ?? Date.now()) - startedAt;

      deps.logger?.info?.("chat:finish", {
        durationMs,
        finishReason,
        model: provider.modelId,
        requestId,
        sessionId,
        userId,
      });

      if (trigger === "submit-message") {
        await persistMemoryTurn({
          logger: deps.logger,
          sessionId,
          turn: createTextMemoryTurn("assistant", text),
          userId,
        });
      }

      const updatedMeta: Json = mergeAssistantMetadata(assistantBaseMetadata, {
        durationMs,
        finishReason,
        isAborted: false,
        status: "completed",
        totalUsage: totalUsage ?? null,
      });

      const content = encodePartsToContent([{ text, type: "text" }]);

      const { error } = await updateSingle(
        deps.supabase,
        "chat_messages",
        { content, metadata: updatedMeta },
        (qb) => qb.eq("id", assistantMessageId).eq("user_id", userId)
      );

      if (error) {
        deps.logger?.warn?.("chat:message_update_failed", {
          error: error instanceof Error ? error.message : String(error),
          requestId,
          sessionId,
          userId,
        });
      }
    },
    onStepFinish: async ({ toolCalls, toolResults }) => {
      if (!toolCalls?.length && !toolResults?.length) {
        return;
      }

      const resultsById = new Map<string, ParsedToolResult>();
      for (const toolResult of toolResults ?? []) {
        const parsed = parseToolResult(toolResult);
        if (parsed) resultsById.set(parsed.toolCallId, parsed);
      }

      const now = nowIso();

      for (const toolCall of toolCalls ?? []) {
        const parsed = parseToolCall(toolCall);
        if (!parsed) continue;
        if (persistedToolCallIds.has(parsed.toolCallId)) continue;

        persistedToolCallIds.add(parsed.toolCallId);
        const maybeResult = resultsById.get(parsed.toolCallId);

        const args = (parsed.args ?? parsed.input ?? {}) as Json;
        const status = maybeResult?.isError ? "failed" : "completed";
        const errorMessage =
          maybeResult?.isError && typeof maybeResult.result === "string"
            ? maybeResult.result
            : null;

        const toolRow = {
          arguments: args,
          // biome-ignore lint/style/useNamingConvention: Database field name
          completed_at: now,
          // biome-ignore lint/style/useNamingConvention: Database field name
          created_at: now,
          // biome-ignore lint/style/useNamingConvention: Database field name
          error_message: errorMessage,
          // biome-ignore lint/style/useNamingConvention: Database field name
          message_id: assistantMessageId,
          result: (maybeResult?.result ?? null) as Json | null,
          status,
          // biome-ignore lint/style/useNamingConvention: Database field name
          tool_id: parsed.toolCallId,
          // biome-ignore lint/style/useNamingConvention: Database field name
          tool_name: parsed.toolName,
        };

        const { error } = await insertSingle(deps.supabase, "chat_tool_calls", toolRow);
        if (error) {
          const persistErrorMessage =
            error instanceof Error
              ? error.message
              : String((error as { message?: unknown }).message ?? error);
          deps.logger?.warn?.("chat:tool_persist_failed", {
            error: persistErrorMessage,
            requestId,
            sessionId,
            toolCallId: parsed.toolCallId,
            toolName: parsed.toolName,
            userId,
          });
        }
      }
    },
    stopWhen: stepCountIs(maxSteps),
    system,
    tools: chatTools,
  });

  return result.toUIMessageStreamResponse({
    consumeSseStream: consumeStream,
    generateMessageId: () => assistantUiMessageId,
    headers: {
      "x-tripsage-session-id": sessionId,
    },
    messageMetadata: ({ part }) => {
      if (part.type === "start") {
        return { sessionId };
      }
      return undefined;
    },
    onError: (error) => {
      deps.logger?.error?.("chat:stream_error", {
        error: error instanceof Error ? error.message : String(error),
        requestId,
        sessionId,
        userId,
      });
      return "An error occurred while processing your request.";
    },
    onFinish: async ({ finishReason, isAborted, responseMessage }) => {
      if (!isAborted) return;

      const durationMs = (deps.clock?.now?.() ?? Date.now()) - startedAt;
      const text = getTextFromUiMessage(responseMessage);

      const updatedMeta: Json = mergeAssistantMetadata(assistantBaseMetadata, {
        durationMs,
        finishReason: finishReason ?? null,
        isAborted: true,
        status: "aborted",
        totalUsage: null,
      });

      const content = text
        ? encodePartsToContent([{ text, type: "text" }])
        : encodePartsToContent([]);

      const { error } = await updateSingle(
        deps.supabase,
        "chat_messages",
        { content, metadata: updatedMeta },
        (qb) => qb.eq("id", assistantMessageId).eq("user_id", userId)
      );

      if (error) {
        deps.logger?.warn?.("chat:aborted_message_update_failed", {
          error: error instanceof Error ? error.message : String(error),
          requestId,
          sessionId,
          userId,
        });
      }
    },
  });
}
