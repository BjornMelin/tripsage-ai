/**
 * @fileoverview Shared test utilities and helpers for user profile store tests.
 */

import { act } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";
import { useUserProfileStore } from "@/stores/user-store";

/**
 * Accelerates store async flows in test suites by mocking setTimeout.
 * Returns a cleanup function that should be called in afterEach.
 */
export const setupTimeoutMock = (): { mockRestore: () => void } => {
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
};

/**
 * Resets the user profile store to its initial state.
 */
export const resetUserProfileStore = (): void => {
  act(() => {
    useUserProfileStore.getState().reset();
  });
};

/**
 * Sets up beforeEach and afterEach hooks for user profile store tests.
 * Includes timeout mocking and store reset.
 */
export const setupUserProfileStoreTests = (): void => {
  let timeoutSpy: { mockRestore: () => void } | null = null;

  beforeEach(() => {
    timeoutSpy = setupTimeoutMock();
    resetUserProfileStore();
  });

  afterEach(() => {
    timeoutSpy?.mockRestore();
  });
};
