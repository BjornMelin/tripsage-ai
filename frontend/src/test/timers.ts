/**
 * Lightweight helpers for short-circuiting timers in tests.
 * Use only when deterministic immediate execution is desired.
 */

export type RestoreFn = () => void;

/**
 * Short-circuits global setTimeout to execute callbacks immediately.
 * Returns a restore function that must be called after the test.
 */
export function shortCircuitSetTimeout(): RestoreFn {
  const g = globalThis as unknown as { setTimeout: typeof setTimeout };
  const original = g.setTimeout;
  g.setTimeout = ((cb: Parameters<typeof setTimeout>[0]) => {
    if (typeof cb === "function") cb();
    return 0 as unknown as ReturnType<typeof setTimeout>;
  }) as typeof setTimeout;
  return () => {
    g.setTimeout = original;
  };
}
