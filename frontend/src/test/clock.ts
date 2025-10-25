/**
 * @fileoverview Test clock utilities for deterministic time control.
 * Use within a suite to activate fake timers and advance the clock.
 */

import { vi } from "vitest";

/**
 * Activate fake timers and optionally set a fixed system time.
 *
 * @param isoTime Optional ISO timestamp to fix Date.now() to.
 */
export function useFakeClock(isoTime?: string): void {
  vi.useFakeTimers();
  if (isoTime) {
    vi.setSystemTime(new Date(isoTime));
  }
}

/**
 * Advance the fake clock by milliseconds.
 *
 * @param ms Milliseconds to advance.
 */
export async function advance(ms: number): Promise<void> {
  await vi.advanceTimersByTimeAsync(ms);
}

/**
 * Run all pending timers in the current fake timer queue.
 */
export async function runAll(): Promise<void> {
  await vi.runAllTimersAsync();
}

/**
 * Restore real timers. Call from `afterEach` or at suite end.
 */
export function restoreRealClock(): void {
  vi.useRealTimers();
}
