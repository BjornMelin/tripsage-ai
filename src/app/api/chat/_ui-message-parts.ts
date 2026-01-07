/**
 * @fileoverview Helpers for parsing/sanitizing persisted UI message parts and rehydrating tool invocations.
 */

import type { UIMessage } from "ai";
import type { ServerLogger } from "@/lib/telemetry/logger";

type UiParts = UIMessage["parts"];

type ToolCallRow = {
  // biome-ignore lint/style/useNamingConvention: Database field name
  tool_name?: unknown;
  // biome-ignore lint/style/useNamingConvention: Database field name
  tool_id?: unknown;
  arguments?: unknown;
  result?: unknown;
  status?: unknown;
  // biome-ignore lint/style/useNamingConvention: Database field name
  error_message?: unknown;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isToolLikeType(type: string): boolean {
  if (type === "dynamic-tool") return true;
  if (type.startsWith("tool-")) return true;

  // Model-only tool parts (tool-call / tool-result / approvals).
  if (
    type === "tool-call" ||
    type === "tool-result" ||
    type === "tool-approval-request" ||
    type === "tool-approval-response"
  ) {
    return true;
  }

  // UI stream chunk types (never valid persisted UIMessage parts).
  if (type.startsWith("tool-input-") || type.startsWith("tool-output-")) return true;

  return false;
}

function sanitizePersistedPart(part: unknown): UiParts[number] | null {
  if (!isRecord(part)) return null;
  const type = part.type;
  if (typeof type !== "string") return null;

  if (isToolLikeType(type)) return null;

  if (type === "text") {
    const text = part.text;
    return typeof text === "string" ? { text, type: "text" } : null;
  }

  if (type === "reasoning") {
    const text = part.text;
    return typeof text === "string" ? { text, type: "reasoning" } : null;
  }

  if (type === "file") {
    const url = part.url;
    const mediaType =
      typeof part.mediaType === "string"
        ? part.mediaType
        : typeof part.mimeType === "string"
          ? part.mimeType
          : undefined;
    if (typeof url !== "string" || typeof mediaType !== "string") return null;
    const filename = typeof part.filename === "string" ? part.filename : undefined;
    return { filename, mediaType, type: "file", url };
  }

  if (type === "source-url") {
    const url = part.url;
    const sourceId = part.sourceId;
    if (typeof url !== "string" || typeof sourceId !== "string") return null;
    const title = typeof part.title === "string" ? part.title : undefined;
    return { sourceId, title, type: "source-url", url };
  }

  if (type === "source-document") {
    const sourceId = part.sourceId;
    const mediaType = part.mediaType;
    const title = part.title;
    if (
      typeof sourceId !== "string" ||
      typeof mediaType !== "string" ||
      typeof title !== "string"
    ) {
      return null;
    }
    const filename = typeof part.filename === "string" ? part.filename : undefined;
    return { filename, mediaType, sourceId, title, type: "source-document" };
  }

  if (type === "step-start") {
    return { type: "step-start" };
  }

  if (type.startsWith("data-")) {
    if (!("data" in part)) return null;
    const id = typeof part.id === "string" ? part.id : undefined;
    return {
      data: part.data,
      id,
      type: type as `data-${string}`,
    } as UiParts[number];
  }

  return null;
}

export function parsePersistedUiParts(options: {
  content: unknown;
  logger?: ServerLogger;
  messageDbId: number;
  sessionId: string;
}): UiParts {
  const { content, logger, messageDbId, sessionId } = options;
  if (typeof content !== "string") return [];
  const trimmed = content.trim();
  if (!trimmed) return [];

  try {
    const parsed = JSON.parse(trimmed) as unknown;
    if (!Array.isArray(parsed)) {
      return [{ text: trimmed, type: "text" }];
    }

    const sanitized: UiParts = [];
    for (const part of parsed) {
      const safe = sanitizePersistedPart(part);
      if (safe) sanitized.push(safe);
    }
    return sanitized;
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

export function rehydrateToolInvocations(toolRows: ToolCallRow[]): UiParts {
  const parts: UiParts = [];

  for (const toolRow of toolRows) {
    if (!toolRow) continue;
    const toolName =
      typeof toolRow.tool_name === "string" && toolRow.tool_name.trim().length > 0
        ? toolRow.tool_name.trim()
        : undefined;
    const toolCallId =
      typeof toolRow.tool_id === "string" && toolRow.tool_id.trim().length > 0
        ? toolRow.tool_id.trim()
        : undefined;

    if (!toolName || !toolCallId) continue;

    const input = toolRow.arguments ?? {};

    const status = typeof toolRow.status === "string" ? toolRow.status : undefined;
    if (status === "failed") {
      const errorText =
        typeof toolRow.error_message === "string" &&
        toolRow.error_message.trim().length > 0
          ? toolRow.error_message
          : typeof toolRow.result === "string" && toolRow.result.trim().length > 0
            ? toolRow.result
            : "Tool failed";

      parts.push({
        errorText,
        input,
        state: "output-error",
        toolCallId,
        toolName,
        type: "dynamic-tool",
      });
      continue;
    }

    if (status === "completed") {
      if (toolRow.result == null) {
        parts.push({
          input,
          state: "input-available",
          toolCallId,
          toolName,
          type: "dynamic-tool",
        });
        continue;
      }

      parts.push({
        input,
        output: toolRow.result,
        state: "output-available",
        toolCallId,
        toolName,
        type: "dynamic-tool",
      });
      continue;
    }

    parts.push({
      input,
      state: "input-available",
      toolCallId,
      toolName,
      type: "dynamic-tool",
    });
  }

  return parts;
}

export function ensureNonEmptyParts(parts: UiParts): UiParts {
  return parts.length > 0 ? parts : [{ text: "", type: "text" }];
}
