/**
 * @fileoverview Helpers to inject session userId into selected AI SDK tools.
 */

/** Wrap tools by name to inject { userId } into their execute input. */
export function wrapToolsWithUserId(
  tools: Record<string, unknown>,
  userId: string,
  onlyKeys: string[]
): Record<string, unknown> {
  const out: Record<string, unknown> = { ...tools };
  for (const k of onlyKeys) {
    const t = out[k] as unknown;
    if (t && typeof (t as { execute?: unknown }).execute === "function") {
      const exec = (t as { execute: (a: unknown, c?: unknown) => Promise<unknown> })
        .execute;
      out[k] = {
        ...(t as Record<string, unknown>),
        execute: (a: Record<string, unknown>, c?: unknown) =>
          exec({ ...(a ?? {}), userId }, c),
      } as Record<string, unknown>;
    }
  }
  return out;
}
