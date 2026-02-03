/**
 * @fileoverview DI handlers for chat sessions/messages routes.
 */

import { safeValidateUIMessages, type UIMessage } from "ai";
import { NextResponse } from "next/server";
import { errorResponse, notFoundResponse } from "@/lib/api/route-helpers";
import { isChatEphemeralEnabled } from "@/lib/chat/ephemeral";
import { extractErrorMessage } from "@/lib/errors/error-message";
import { nowIso, secureUuid } from "@/lib/security/random";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import {
  deleteSingle,
  getMany,
  getMaybeSingle,
  insertSingle,
} from "@/lib/supabase/typed-helpers";
import type { ServerLogger } from "@/lib/telemetry/logger";
import { getUiMessageIdFromRow, isSupersededMessage } from "../_metadata-helpers";
import {
  ensureNonEmptyParts,
  parsePersistedUiParts,
  rehydrateToolInvocations,
} from "../_ui-message-parts";

/**
 * Dependencies interface for sessions handlers.
 */
export interface SessionsDeps {
  supabase: TypedServerSupabase;
  userId: string;
  logger: ServerLogger;
}

/**
 * Create a chat session owned by the authenticated user.
 *
 * @param deps - Collaborators with Supabase client and authenticated userId.
 * @param title - Optional title (stored in metadata).
 * @returns Response with the created session ID.
 */
export async function createSession(
  deps: SessionsDeps,
  title?: string
): Promise<Response> {
  const allowEphemeral = isChatEphemeralEnabled();
  const id = secureUuid();
  const now = nowIso();
  const { error } = await insertSingle(
    deps.supabase,
    "chat_sessions",
    {
      // biome-ignore lint/style/useNamingConvention: Database field name
      created_at: now,
      id,
      metadata: title ? { title } : {},
      // biome-ignore lint/style/useNamingConvention: Database field name
      updated_at: now,
      // biome-ignore lint/style/useNamingConvention: Database field name
      user_id: deps.userId,
    },
    { select: "id", validate: false }
  );
  if (error) {
    if (allowEphemeral) {
      deps.logger.warn("chat:session_create_skipped", {
        error: extractErrorMessage(error),
        userId: deps.userId,
      });
      return NextResponse.json({ id }, { status: 201 });
    }
    return errorResponse({
      error: "db_error",
      reason: "Failed to create session",
      status: 500,
    });
  }
  return NextResponse.json({ id }, { status: 201 });
}

/**
 * List sessions for the authenticated user.
 *
 * @param deps - Collaborators with Supabase client and authenticated userId.
 * @returns Response with the list of sessions.
 */
export async function listSessions(deps: SessionsDeps): Promise<Response> {
  const allowEphemeral = isChatEphemeralEnabled();
  const { data, error } = await getMany(
    deps.supabase,
    "chat_sessions",
    (qb) => qb.eq("user_id", deps.userId),
    {
      ascending: false,
      orderBy: "updated_at",
      select: "id, created_at, updated_at, metadata",
      validate: false,
    }
  );
  if (error) {
    if (allowEphemeral) {
      deps.logger.warn("chat:sessions_list_skipped", {
        error: extractErrorMessage(error),
        userId: deps.userId,
      });
      return NextResponse.json([], { status: 200 });
    }
    return errorResponse({
      error: "db_error",
      reason: "Failed to list sessions",
      status: 500,
    });
  }
  return NextResponse.json(data ?? [], { status: 200 });
}

/**
 * Get a single session by id (owner-only).
 *
 * @param deps - Collaborators with Supabase client and authenticated userId.
 * @param id - The ID of the session to retrieve.
 * @returns Response with the session data.
 */
export async function getSession(deps: SessionsDeps, id: string): Promise<Response> {
  const { data, error } = await getMaybeSingle(
    deps.supabase,
    "chat_sessions",
    (qb) => qb.eq("id", id).eq("user_id", deps.userId),
    { select: "id, created_at, updated_at, metadata", validate: false }
  );
  if (error)
    return errorResponse({
      error: "db_error",
      reason: "Failed to get session",
      status: 500,
    });
  if (!data) return notFoundResponse("Session");
  return NextResponse.json(data, { status: 200 });
}

/**
 * Delete a session by id (owner-only).
 *
 * @param deps - Collaborators with Supabase client and authenticated userId.
 * @param id - The ID of the session to delete.
 * @returns Response with no content on success.
 */
export async function deleteSession(deps: SessionsDeps, id: string): Promise<Response> {
  const { count, error } = await deleteSingle(
    deps.supabase,
    "chat_sessions",
    (qb) => qb.eq("id", id).eq("user_id", deps.userId),
    { count: "exact", returning: "representation", select: "id" }
  );
  if (error)
    return errorResponse({
      error: "db_error",
      reason: "Failed to delete session",
      status: 500,
    });
  if (count === 0) return notFoundResponse("Session");
  return new Response(null, { status: 204 });
}

/**
 * List messages for a session.
 *
 * @param deps - Collaborators with Supabase client and authenticated userId.
 * @param id - The ID of the session to list messages for.
 * @returns Response with the list of session messages.
 */
export async function listMessages(deps: SessionsDeps, id: string): Promise<Response> {
  const logger = deps.logger;

  const sessionPromise = getMaybeSingle(
    deps.supabase,
    "chat_sessions",
    (qb) => qb.eq("id", id).eq("user_id", deps.userId),
    { select: "id", validate: false }
  );

  const messagesPromise = getMany(
    deps.supabase,
    "chat_messages",
    (qb) => qb.eq("session_id", id).eq("user_id", deps.userId),
    {
      ascending: true,
      orderBy: "id",
      select: "id, role, content, created_at, metadata",
      validate: false,
    }
  );

  const [
    { data: session, error: sessionError },
    { data: messages, error: messageError },
  ] = await Promise.all([sessionPromise, messagesPromise]);

  if (sessionError) {
    return errorResponse({
      error: "db_error",
      reason: "Failed to verify session",
      status: 500,
    });
  }
  if (!session) return notFoundResponse("Session");

  if (messageError)
    return errorResponse({
      error: "db_error",
      reason: "Failed to list messages",
      status: 500,
    });

  const visibleMessages = (messages ?? []).filter(
    (row) => !isSupersededMessage(row.metadata)
  );

  const messageIds = visibleMessages
    .map((m) => m.id)
    .filter((value): value is number => typeof value === "number");

  const { data: toolCalls, error: toolError } =
    messageIds.length > 0
      ? await getMany(
          deps.supabase,
          "chat_tool_calls",
          (qb) => qb.in("message_id", messageIds),
          {
            ascending: true,
            orderBy: "id",
            select:
              "message_id, tool_id, tool_name, arguments, result, status, error_message",
            validate: false,
          }
        )
      : { data: [], error: null };

  if (toolError) {
    return errorResponse({
      error: "db_error",
      reason: "Failed to list tool calls",
      status: 500,
    });
  }

  const toolCallsByMessageId = new Map<number, Array<(typeof toolCalls)[number]>>();
  for (const toolCall of toolCalls ?? []) {
    const messageId = toolCall.message_id;
    if (typeof messageId !== "number") continue;
    const existing = toolCallsByMessageId.get(messageId) ?? [];
    existing.push(toolCall);
    toolCallsByMessageId.set(messageId, existing);
  }

  const rawUiMessages = visibleMessages.map((row) => {
    const baseParts = parsePersistedUiParts({
      content: row.content,
      logger,
      messageDbId: row.id,
      sessionId: id,
    });
    const uiMessageId = getUiMessageIdFromRow({
      id: row.id,
      metadata: row.metadata,
    });

    let role: "assistant" | "system" | "user";
    if (row.role === "user" || row.role === "assistant" || row.role === "system") {
      role = row.role;
    } else {
      logger.warn("Unexpected message role value; defaulting to assistant", {
        messageId: row.id,
        role: row.role,
        sessionId: id,
      });
      role = "assistant";
    }

    const enrichedParts = [...baseParts];
    const toolRows = toolCallsByMessageId.get(row.id) ?? [];

    if (toolRows.length > 0 && role === "assistant") {
      const toolParts = rehydrateToolInvocations(toolRows);
      if (toolParts.length !== toolRows.length) {
        logger.warn("Some tool calls were skipped due to missing identifiers", {
          hydratedToolCalls: toolParts.length,
          messageId: row.id,
          sessionId: id,
          totalToolCalls: toolRows.length,
        });
      }
      enrichedParts.push(...toolParts);
    }

    const metadata =
      row.metadata && typeof row.metadata === "object" && !Array.isArray(row.metadata)
        ? row.metadata
        : undefined;

    return {
      id: uiMessageId,
      metadata,
      parts: ensureNonEmptyParts(enrichedParts),
      role,
    };
  });

  if (rawUiMessages.length === 0) {
    return NextResponse.json([], { status: 200 });
  }

  const validated = await safeValidateUIMessages({ messages: rawUiMessages });
  if (!validated.success) {
    const normalizedError =
      validated.error instanceof Error
        ? validated.error
        : new Error(String(validated.error ?? "Invalid stored messages"));

    logger.error("Failed to parse stored messages", {
      error: normalizedError.message,
      sessionId: id,
    });

    return errorResponse({
      error: "internal",
      reason: "Failed to parse stored messages",
      status: 500,
    });
  }

  return NextResponse.json(validated.data satisfies UIMessage[], { status: 200 });
}

/**
 * Create a message within a session for the authenticated user.
 *
 * @param deps - Collaborators with Supabase client and authenticated userId.
 * @param id - The ID of the session to create a message in.
 * @param payload - Message role and content parts.
 * @returns Response with no content on success.
 */
export async function createMessage(
  deps: SessionsDeps,
  id: string,
  payload: { role?: string; parts?: unknown[] }
): Promise<Response> {
  if (!payload?.role || typeof payload.role !== "string")
    return errorResponse({
      error: "bad_request",
      reason: "Role is required",
      status: 400,
    });
  const normalizedRole = payload.role.toLowerCase();
  if (!["user", "assistant", "system"].includes(normalizedRole)) {
    return errorResponse({
      error: "bad_request",
      reason: "Role must be user, assistant, or system",
      status: 400,
    });
  }
  const { data: session, error: sessionError } = await getMaybeSingle(
    deps.supabase,
    "chat_sessions",
    (qb) => qb.eq("id", id).eq("user_id", deps.userId),
    { select: "id", validate: false }
  );
  if (sessionError)
    return errorResponse({
      error: "db_error",
      reason: "Failed to verify session",
      status: 500,
    });
  if (!session) return notFoundResponse("Session");
  const content = JSON.stringify(payload.parts ?? []);
  const { error } = await insertSingle(
    deps.supabase,
    "chat_messages",
    {
      content,
      metadata: {},
      role: normalizedRole as "user" | "system" | "assistant",
      // biome-ignore lint/style/useNamingConvention: Database field name
      session_id: id,
      // biome-ignore lint/style/useNamingConvention: Database field name
      user_id: deps.userId,
    },
    { select: "id", validate: false }
  );
  if (error)
    return errorResponse({
      error: "db_error",
      reason: "Failed to create message",
      status: 500,
    });
  return new Response(null, { status: 201 });
}
