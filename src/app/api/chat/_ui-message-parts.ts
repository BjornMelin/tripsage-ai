/**
 * @fileoverview Helpers for parsing/sanitizing persisted UI message parts and rehydrating tool invocations.
 */

import type { UIMessage } from "ai";
import { z } from "zod";
import type { ServerLogger } from "@/lib/telemetry/logger";

type UiParts = UIMessage["parts"];

const MEDIA_TYPE_PATTERN =
  /^[!#$%&'*+\-.^_`|~0-9A-Za-z]+(?:\/[!#$%&'*+\-.^_`|~0-9A-Za-z]+)?$/;
const BASE64_PATTERN = /^[A-Za-z0-9+/]+={0,2}$/;
const openAiItemMetadataSchema = z.object({
  itemId: z.string().min(1),
});
const openAiReasoningMetadataSchema = z
  .object({
    itemId: z.string().min(1).optional(),
    reasoningEncryptedContent: z.string().min(1).nullable().optional(),
  })
  .refine(
    (metadata) =>
      metadata.itemId !== undefined ||
      typeof metadata.reasoningEncryptedContent === "string"
  );
const openAiCompactionMetadataSchema = z.object({
  encryptedContent: z.string().min(1).optional(),
  itemId: z.string().min(1),
  type: z.literal("compaction"),
});

type ToolCallRow = {
  // biome-ignore lint/style/useNamingConvention: Database field name
  tool_name?: unknown;
  // biome-ignore lint/style/useNamingConvention: Database field name
  tool_id?: unknown;
  arguments?: unknown;
  result?: unknown;
  status?: unknown;
  // biome-ignore lint/style/useNamingConvention: Database field name
  provider_executed?: unknown;
  // biome-ignore lint/style/useNamingConvention: Database field name
  error_message?: unknown;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function getOpenAiMetadata(value: unknown): unknown {
  if (!isRecord(value) || !isRecord(value.openai)) return undefined;
  return value.openai;
}

function sanitizeOpenAiItemMetadata(value: unknown) {
  const parsed = openAiItemMetadataSchema.safeParse(getOpenAiMetadata(value));
  return parsed.success ? { openai: parsed.data } : undefined;
}

function sanitizeOpenAiReasoningMetadata(value: unknown) {
  const parsed = openAiReasoningMetadataSchema.safeParse(getOpenAiMetadata(value));
  return parsed.success ? { openai: parsed.data } : undefined;
}

function sanitizeOpenAiCompactionMetadata(value: unknown) {
  const parsed = openAiCompactionMetadataSchema.safeParse(getOpenAiMetadata(value));
  return parsed.success ? { openai: parsed.data } : undefined;
}

function isPersistedToolPartType(type: string): boolean {
  return (
    type === "dynamic-tool" ||
    type.startsWith("tool-") ||
    type.startsWith("tool-input-") ||
    type.startsWith("tool-output-")
  );
}

function getStaticToolPartType(toolName: string): `tool-${string}` {
  return `tool-${toolName}`;
}

function sanitizeFileFields(part: Record<string, unknown>): {
  mediaType: string;
  url: string;
} | null {
  const rawMediaType =
    typeof part.mediaType === "string"
      ? part.mediaType
      : typeof part.mimeType === "string"
        ? part.mimeType
        : undefined;
  if (typeof part.url !== "string" || !rawMediaType) return null;

  const mediaType = rawMediaType.trim().toLowerCase();
  const url = part.url.trim();
  if (
    !MEDIA_TYPE_PATTERN.test(mediaType) ||
    (part.type === "reasoning-file" &&
      (!mediaType.includes("/") || mediaType.endsWith("/*"))) ||
    !url
  ) {
    return null;
  }

  let protocol: string;
  try {
    protocol = new URL(url).protocol;
  } catch {
    return null;
  }

  if (protocol === "http:" || protocol === "https:") return { mediaType, url };
  if (protocol !== "data:") return null;

  const prefix = `data:${mediaType};base64,`;
  if (url.slice(0, prefix.length).toLowerCase() !== prefix) return null;
  const data = url.slice(prefix.length);
  if (data.length === 0 || data.length % 4 !== 0 || !BASE64_PATTERN.test(data)) {
    return null;
  }

  return { mediaType, url };
}

function sanitizePersistedPart(part: unknown): UiParts[number] | null {
  if (!isRecord(part)) return null;
  const type = part.type;
  if (typeof type !== "string") return null;

  if (isPersistedToolPartType(type)) return null;

  if (type === "text") {
    const text = part.text;
    if (typeof text !== "string") return null;
    const providerMetadata = sanitizeOpenAiItemMetadata(part.providerMetadata);
    return {
      ...(providerMetadata ? { providerMetadata } : {}),
      text,
      type: "text",
    };
  }

  if (type === "reasoning") {
    const text = part.text;
    if (typeof text !== "string") return null;
    const providerMetadata = sanitizeOpenAiReasoningMetadata(part.providerMetadata);
    return {
      ...(providerMetadata ? { providerMetadata } : {}),
      text,
      type: "reasoning",
    };
  }

  if (type === "custom" && part.kind === "openai.compaction") {
    const providerMetadata = sanitizeOpenAiCompactionMetadata(part.providerMetadata);
    return providerMetadata
      ? {
          kind: "openai.compaction",
          providerMetadata,
          type: "custom",
        }
      : null;
  }

  if (type === "file" || type === "reasoning-file") {
    const fields = sanitizeFileFields(part);
    if (!fields) return null;
    if (type === "reasoning-file") {
      return { ...fields, type: "reasoning-file" };
    }
    const filename = typeof part.filename === "string" ? part.filename : undefined;
    return { filename, ...fields, type: "file" };
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

/**
 * Keep only canonical, non-tool UI message parts that are safe to persist.
 *
 * Tool lifecycle state is stored separately in `chat_tool_calls`; unsupported or
 * malformed parts are dropped at the persistence boundary.
 *
 * @param parts UI message parts from a stream or persistence boundary.
 * @returns Canonical non-tool parts that are safe to persist.
 * @see docs/architecture/decisions/adr-0074-ai-sdk-v7-provider-v4-and-stateless-streams.md
 */
export function sanitizePersistableUiParts(
  parts: readonly unknown[] | undefined
): UiParts {
  if (!Array.isArray(parts)) return [];

  const sanitized: UiParts = [];
  for (const part of parts) {
    const safe = sanitizePersistedPart(part);
    if (safe) sanitized.push(safe);
  }
  return sanitized;
}

/**
 * Parses persisted UI message parts from stored JSON content.
 *
 * Accepts a JSON string (or non-string) and returns sanitized UI parts using
 * `sanitizePersistedPart`. Invalid input or parse errors return a single text
 * part fallback and log a warning when a logger is provided.
 */
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

    return sanitizePersistableUiParts(parsed);
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

/**
 * Rehydrates tool invocation rows into AI SDK v7 static tool UI parts.
 *
 * Expects `toolRows` with fields like `tool_name`, `tool_id`, `arguments`,
 * `status` ("completed" | "failed"), `provider_executed`, `result`, and
 * `error_message`. Returns `tool-${toolName}` parts with state
 * (`input-available`, `output-available`, or `output-error`) plus input/output
 * and error text when applicable. `chat_tool_calls` is the authoritative
 * lifecycle store; persisted message content must not own tool state.
 *
 * @param toolRows - Persisted `chat_tool_calls` rows to rehydrate.
 * @returns AI SDK v7 static tool UI parts for the assistant message.
 */
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
    const type = getStaticToolPartType(toolName);

    const status = typeof toolRow.status === "string" ? toolRow.status : undefined;
    const providerExecuted =
      typeof toolRow.provider_executed === "boolean"
        ? toolRow.provider_executed
        : false;
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
        providerExecuted,
        state: "output-error",
        toolCallId,
        type,
      });
      continue;
    }

    if (status === "completed") {
      if (toolRow.result == null) {
        parts.push({
          input,
          output: null,
          providerExecuted,
          state: "output-available",
          toolCallId,
          type,
        });
        continue;
      }

      parts.push({
        input,
        output: toolRow.result,
        providerExecuted,
        state: "output-available",
        toolCallId,
        type,
      });
      continue;
    }

    parts.push({
      input,
      providerExecuted,
      state: "input-available",
      toolCallId,
      type,
    });
  }

  return parts;
}

/**
 * Ensures the parts array contains at least one element.
 *
 * Returns the original parts when non-empty, otherwise a single empty text
 * part fallback.
 */
export function ensureNonEmptyParts(parts: UiParts): UiParts {
  return parts.length > 0 ? parts : [{ text: "", type: "text" }];
}
