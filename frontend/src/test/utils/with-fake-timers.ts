/**
 * @fileoverview Selective fake timer utility for Vitest tests.
 *
 * This utility provides opt-in fake timer support for tests that need to control time.
 * Unlike global fake timers, this approach only applies timers to tests that explicitly
 * need them, reducing overhead for tests that don't manipulate time.
 *
 * @example
 * ```typescript
 * import { withFakeTimers } from '@/test/utils/with-fake-timers';
 *
 * test('handles debounced input', withFakeTimers(async () => {
 *   const { getByRole } = render(<SearchInput />);
 *   const input = getByRole('textbox');
 *
 *   fireEvent.change(input, { target: { value: 'test' } });
 *   vi.advanceTimersByTime(300); // Advance debounce timer
 *
 *   await waitFor(() => {
 *     expect(mockSearch).toHaveBeenCalled();
 *   });
 * }));
 * ```
 */

import { vi } from "vitest";

/**
 * Wraps a test function with fake timer setup and cleanup.
 *
 * This utility automatically:
 * - Enables fake timers before the test
 * - Runs pending timers after the test
 * - Clears all timers
 * - Restores real timers
 *
 * @param testFn The test function to wrap with fake timers
 * @returns A wrapped test function that uses fake timers
 */
export const withFakeTimers = (
  testFn: () => void | Promise<void>
): (() => Promise<void>) => {
  return async () => {
    vi.useFakeTimers();
    try {
      await testFn();
    } finally {
      vi.runOnlyPendingTimers();
      vi.clearAllTimers();
      vi.useRealTimers();
    }
  };
};

/**
 * Creates a test context with fake timers enabled.
 * Use this in beforeEach/afterEach when multiple tests in a suite need fake timers.
 *
 * @example
 * ```typescript
 * import { createFakeTimersContext } from '@/test/utils/with-fake-timers';
 *
 * describe('Time-dependent suite', () => {
 *   const timers = createFakeTimersContext();
 *
 *   beforeEach(timers.setup);
 *   afterEach(timers.teardown);
 *
 *   test('first test', () => {
 *     vi.advanceTimersByTime(1000);
 *     // test code
 *   });
 * });
 * ```
 */
export const createFakeTimersContext = () => {
  return {
    setup: () => {
      vi.useFakeTimers();
    },
    teardown: () => {
      vi.runOnlyPendingTimers();
      vi.clearAllTimers();
      vi.useRealTimers();
    },
  };
};
