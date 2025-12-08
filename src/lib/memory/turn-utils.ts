/**
 * @fileoverview Helpers for converting chat payloads into memory turns
 * and persisting them through the orchestrator.
 */

import "server-only";

import type { Message, MessageRole } from "@schemas/chat";
import type { UIMessage } from "ai";
import { handleMemoryIntent } from "@/lib/memory/orchestrator";
import { nowIso, secureUuid } from "@/lib/security/random";

type ConversationRole = Extract<MessageRole, "assistant" | "user">;

/**
 * Checks if a value is a record.
 *
 * @param value - The value to check.
 * @returns True if the value is a record, false otherwise.
 */
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/**
 * Flattens a list of text parts into a single string.
 * @param value - The value to flatten.
 * @returns A string.
 */
function flattenTextParts(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }
  if (!Array.isArray(value)) {
    return "";
  }

  return value
    .map((part) => {
      if (typeof part === "string") {
        return part;
      }
      if (!isRecord(part)) {
        return "";
      }
      const maybeText = part.text;
      return typeof maybeText === "string" ? maybeText : "";
    })
    .filter((segment) => segment.length > 0)
    .join("\n")
    .trim();
}

/**
 * Creates a memory turn from a text.
 *
 * @param role - The role of the turn.
 * @param content - The content of the turn.
 * @param overrides - The overrides to apply to the turn.
 * @returns A memory turn.
 */
function createMemoryTurn(
  role: ConversationRole,
  content: string,
  overrides: { id?: string; timestamp?: string } = {}
): Message | null {
  const normalized = content.trim();
  if (!normalized) {
    return null;
  }

  return {
    attachments: [],
    content: normalized,
    id: overrides.id ?? secureUuid(),
    role,
    timestamp: overrides.timestamp ?? nowIso(),
    toolCalls: [],
    toolResults: [],
  };
}

/**
 * Converts a UI message to a memory turn.
 *
 * @param message - The UI message to convert.
 * @returns A memory turn or null if the message is not a user or assistant message.
 */
export function uiMessageToMemoryTurn(message: UIMessage): Message | null {
  if (message.role !== "user" && message.role !== "assistant") {
    return null;
  }

  const text = flattenTextParts(message.parts);
  return createMemoryTurn(message.role, text, { id: message.id });
}

/**
 * Creates a memory turn from a text.
 *
 * @param role - The role of the turn.
 * @param content - The content of the turn.
 * @returns A memory turn.
 */
export function createTextMemoryTurn(
  role: ConversationRole,
  content: string
): Message | null {
  return createMemoryTurn(role, content);
}

/**
 * Converts a list of messages to a memory turn.
 *
 * @param messages - The messages to convert.
 * @returns A memory turn or null if no assistant messages are found.
 */
export function assistantResponseToMemoryTurn(messages: unknown[]): Message | null {
  for (const message of messages) {
    if (!isRecord(message)) {
      continue;
    }
    if (message.role !== "assistant") {
      continue;
    }

    const text = flattenTextParts(message.content);
    const id = typeof message.id === "string" ? message.id : undefined;
    const turn = createMemoryTurn("assistant", text, { id });
    if (turn) {
      return turn;
    }
  }
  return null;
}

/**
 * Persists a memory turn to the database.
 *
 * @param logger - The logger to use.
 * @param sessionId - The session ID.
 * @param turn - The turn to persist.
 * @param userId - The user ID.
 * @returns A promise that resolves when the turn is persisted.
 */
export async function persistMemoryTurn({
  logger,
  sessionId,
  turn,
  userId,
}: {
  logger?: { error?: (msg: string, meta?: Record<string, unknown>) => void };
  sessionId?: string | null;
  turn: Message | null;
  userId: string;
}): Promise<void> {
  if (!sessionId || !turn) {
    return;
  }

  try {
    await handleMemoryIntent({
      sessionId,
      turn,
      type: "onTurnCommitted",
      userId,
    });
  } catch (error) {
    logger?.error?.("memory.persist_failed", {
      error: error instanceof Error ? error.message : String(error),
      sessionId,
      turnRole: turn.role,
      userId,
    });
  }
}
