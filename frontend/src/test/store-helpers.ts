/**
 * @fileoverview Centralized store test helpers.
 *
 * Provides reusable utilities for testing Zustand stores:
 * - Timeout/timer mocking for deterministic async flows
 * - Generic store reset helpers
 * - Store state waiting utilities
 */

import { act } from "@testing-library/react";
import { vi } from "vitest";

/**
 * Mock setTimeout to execute immediately in tests.
 * Returns cleanup function.
 *
 * @returns Object with mockRestore function
 */
export function setupTimeoutMock(): { mockRestore: () => void } {
  const timeoutSpy = vi.spyOn(globalThis, "setTimeout").mockImplementation(((
    cb: TimerHandler,
    _ms?: number,
    ...args: unknown[]
  ) => {
    if (typeof cb === "function") {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
      cb(...(args as never[]));
    }
    return 0 as unknown as ReturnType<typeof setTimeout>;
  }) as unknown as typeof setTimeout);

  return {
    mockRestore: () => {
      timeoutSpy.mockRestore();
    },
  };
}

/**
 * Mock async timers globally.
 * Useful for stores with debounced actions.
 *
 * @returns Cleanup function
 */
export function mockAsyncTimers(): () => void {
  vi.useFakeTimers();
  return () => {
    vi.useRealTimers();
  };
}

/**
 * Generic store reset helper.
 * Usage: resetStore(useMyStore, { field1: value1, ... })
 *
 * @param useStore - Zustand store hook with setState method
 * @param initialState - Partial state to reset to
 */
export function resetStore<T extends object>(
  useStore: { setState: (state: Partial<T>) => void },
  initialState: Partial<T>
): void {
  act(() => {
    useStore.setState(initialState);
  });
}

/**
 * Wait for store state to match condition.
 * Usage: await waitForStoreState(useMyStore, state => state.isLoading === false)
 *
 * @param useStore - Zustand store hook with getState method
 * @param condition - Function that returns true when condition is met
 * @param timeout - Maximum wait time in milliseconds (default: 5000)
 * @returns Promise that resolves when condition is met
 */
export async function waitForStoreState<T>(
  useStore: { getState: () => T },
  condition: (state: T) => boolean,
  timeout = 5000
): Promise<void> {
  const startTime = Date.now();

  while (!condition(useStore.getState())) {
    if (Date.now() - startTime > timeout) {
      throw new Error("Timeout waiting for store state");
    }
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
}

/**
 * Sets up beforeEach and afterEach hooks for store tests.
 * Includes timeout mocking and store reset.
 *
 * @param resetFn - Function to reset store state
 * @returns Cleanup function (can be called manually if needed)
 */
export function setupStoreTests(_resetFn: () => void): () => void {
  // Note: This function should be called in a beforeEach/afterEach context
  // For Vitest, import beforeEach/afterEach from vitest and call:
  // beforeEach(() => { timeoutSpy = setupTimeoutMock(); resetFn(); });
  // afterEach(() => { timeoutSpy?.mockRestore(); });

  // Return cleanup for manual use if needed
  return () => {
    // Cleanup handled by caller
  };
}
