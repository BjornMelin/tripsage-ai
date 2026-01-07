/**
 * @fileoverview Helpers to inject user context into AI SDK tools.
 */

import "server-only";

type ToolWithExecute = {
  description?: string;
  execute?: (params: unknown, callOptions?: unknown) => Promise<unknown> | unknown;
  inputSchema?: unknown;
  name?: string;
};

function sanitizeToolInput(input: unknown): Record<string, unknown> {
  const baseInput =
    input && typeof input === "object" && !Array.isArray(input)
      ? (input as Record<string, unknown>)
      : {};

  const visited = new WeakMap<object, unknown>();

  const sanitizeValue = (value: unknown): unknown => {
    if (!value || typeof value !== "object") return value;

    const existing = visited.get(value);
    if (existing) return existing;

    if (Array.isArray(value)) {
      const sanitized: unknown[] = [];
      visited.set(value, sanitized);
      for (const entry of value) {
        sanitized.push(sanitizeValue(entry));
      }
      return sanitized;
    }

    const proto = Object.getPrototypeOf(value);
    const isPlainObject = proto === Object.prototype || proto === null;
    if (!isPlainObject) {
      return value;
    }

    const sanitized = Object.create(null) as Record<string, unknown>;
    visited.set(value, sanitized);

    for (const [key, nested] of Object.entries(value as Record<string, unknown>)) {
      if (key === "__proto__" || key === "constructor" || key === "prototype") {
        continue;
      }
      sanitized[key] = sanitizeValue(nested);
    }

    return sanitized;
  };

  return sanitizeValue(baseInput) as Record<string, unknown>;
}

/**
 * Wrap tools by name to inject `{ userId, sessionId? }` into their execute input.
 *
 * The original tools object is left untouched; a shallow copy is returned with
 * wrapped execute functions for the selected keys.
 *
 * @param tools Record of tool definitions to wrap.
 * @param userId User identifier to inject.
 * @param onlyKeys Array of tool names to wrap (others pass through unchanged).
 * @param sessionId Optional session identifier to inject.
 * @returns Record of wrapped tools with injected context.
 */
export function wrapToolsWithUserId<T extends Record<string, unknown>>(
  tools: T,
  userId: string,
  onlyKeys: string[],
  sessionId?: string
): T {
  if (onlyKeys.length === 0) {
    return tools;
  }

  const wrapped: Record<string, unknown> = { ...tools };

  for (const key of onlyKeys) {
    const tool = wrapped[key] as ToolWithExecute | undefined;
    if (!tool || typeof tool !== "object") {
      continue;
    }

    const exec = (tool as ToolWithExecute).execute;
    if (typeof exec !== "function") {
      continue;
    }

    const baseTool = tool as Record<string, unknown>;
    const wrappedTool: ToolWithExecute = {
      ...baseTool,
      execute(input: unknown, callOptions?: unknown) {
        const injected = sanitizeToolInput(input);
        injected.userId = userId;
        if (sessionId) {
          injected.sessionId = sessionId;
        }
        return Promise.resolve().then(() => exec(injected, callOptions));
      },
    };

    (wrapped as Record<string, ToolWithExecute>)[key] = wrappedTool;
  }

  return wrapped as T;
}

/**
 * Wrap tools by name to inject `{ chatId }` into their execute input.
 *
 * Intended for chat-scoped tools that must always operate on the active session.
 *
 * @param tools Record of tool definitions to wrap.
 * @param chatId Chat session identifier to inject.
 * @param onlyKeys Array of tool names to wrap (others pass through unchanged).
 * @returns Record of wrapped tools with injected context.
 */
export function wrapToolsWithChatId<T extends Record<string, unknown>>(
  tools: T,
  chatId: string | undefined,
  onlyKeys: string[]
): T {
  if (!chatId) {
    return tools;
  }

  if (onlyKeys.length === 0) {
    return tools;
  }

  const wrapped: Record<string, unknown> = { ...tools };

  for (const key of onlyKeys) {
    const tool = wrapped[key] as ToolWithExecute | undefined;
    if (!tool || typeof tool !== "object") {
      continue;
    }

    const exec = (tool as ToolWithExecute).execute;
    if (typeof exec !== "function") {
      continue;
    }

    const baseTool = tool as Record<string, unknown>;
    const wrappedTool: ToolWithExecute = {
      ...baseTool,
      execute(input: unknown, callOptions?: unknown) {
        const injected = sanitizeToolInput(input);
        injected.chatId = chatId;
        return Promise.resolve().then(() => exec(injected, callOptions));
      },
    };

    (wrapped as Record<string, ToolWithExecute>)[key] = wrappedTool;
  }

  return wrapped as T;
}
