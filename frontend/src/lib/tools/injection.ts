/**
 * @fileoverview Helpers to inject session userId and sessionId into selected AI SDK tools.
 */

/**
 * Wrap tools by name to inject { userId, sessionId } into their execute input.
 *
 * @param tools - Record of tool definitions to wrap.
 * @param userId - User identifier to inject.
 * @param sessionId - Optional session identifier to inject.
 * @param onlyKeys - Array of tool names to wrap (others pass through unchanged).
 * @returns Record of wrapped tools with injected context.
 */
export function wrapToolsWithUserId(
  tools: Record<string, unknown>,
  userId: string,
  onlyKeys: string[],
  sessionId?: string
): Record<string, unknown> {
  const out: Record<string, unknown> = { ...tools };
  for (const k of onlyKeys) {
    const t = out[k] as unknown;
    if (t && typeof (t as { execute?: unknown }).execute === "function") {
      const exec = (t as { execute: (a: unknown, c?: unknown) => Promise<unknown> })
        .execute;
      out[k] = {
        ...(t as Record<string, unknown>),
        execute: (a: Record<string, unknown>, c?: unknown) => {
          const injected: Record<string, unknown> = { ...(a ?? {}), userId };
          if (sessionId) {
            injected.sessionId = sessionId;
          }
          return exec(injected, c);
        },
      } as Record<string, unknown>;
    }
  }
  return out;
}
