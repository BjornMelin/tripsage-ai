/**
 * @fileoverview Helpers to inject user context into AI SDK tools.
 *
 * Used by chat streaming to ensure selected tools always receive userId and
 * optional sessionId in their input payloads, without mutating the original
 * tool registry.
 */

import "server-only";

type ToolWithExecute = {
  description?: string;
  execute?: (params: unknown, callOptions?: unknown) => Promise<unknown> | unknown;
  inputSchema?: unknown;
  name?: string;
};

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
// biome-ignore lint/style/useNamingConvention: Generic type alias is conventional.
export function wrapToolsWithUserId(
  tools: Record<string, unknown>,
  userId: string,
  onlyKeys: string[],
  sessionId?: string
): Record<string, unknown> {
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
      async execute(input: unknown, callOptions?: unknown) {
        const baseInput =
          input && typeof input === "object" ? (input as Record<string, unknown>) : {};
        const injected: Record<string, unknown> = {
          ...baseInput,
          userId,
        };
        if (sessionId) {
          injected.sessionId = sessionId;
        }
        const result = exec(injected, callOptions);
        return await result;
      },
    };

    (wrapped as Record<string, ToolWithExecute>)[key] = wrappedTool;
  }

  return wrapped;
}
