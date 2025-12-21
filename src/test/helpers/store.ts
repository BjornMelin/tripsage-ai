/**
 * @fileoverview Centralized store test helpers.
 *
 * Provides reusable utilities for testing Zustand stores:
 * - Timeout/timer mocking for deterministic async flows
 */

import { vi } from "vitest";

/**
 * Mock setTimeout to execute immediately in tests.
 * Returns cleanup function.
 *
 * @returns Object with mockRestore function
 */
export function setupTimeoutMock(): { mockRestore: () => void } {
  const originalSetTimeout = globalThis.setTimeout;

  const timeoutSpy = vi
    .spyOn(globalThis, "setTimeout")
    .mockImplementation((cb: TimerHandler, _ms?: number, ...args: unknown[]) => {
      if (typeof cb === "function") {
        cb(...(args as never[]));
      }
      const handle = originalSetTimeout(() => undefined, 0);
      if (typeof handle === "object" && handle && "unref" in handle) {
        (handle as { unref?: () => void }).unref?.();
      }
      return handle;
    });

  return {
    mockRestore: () => {
      timeoutSpy.mockRestore();
    },
  };
}
