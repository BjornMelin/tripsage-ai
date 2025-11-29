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
 * Options for fake timer configuration.
 */
export interface FakeTimersOptions {
  /**
   * When true, time advances automatically during await expressions.
   * Essential for tests that combine fake timers with async operations like MSW.
   * @default false
   */
  shouldAdvanceTime?: boolean;
}

/**
 * Creates a test context with fake timers enabled.
 * Use this in beforeEach/afterEach when multiple tests in a suite need fake timers.
 *
 * @param options - Configuration for fake timers
 * @example
 * ```typescript
 * import { createFakeTimersContext } from '@/test/utils/with-fake-timers';
 *
 * describe('Time-dependent suite', () => {
 *   // Use shouldAdvanceTime when combining with async operations (MSW, fetch)
 *   const timers = createFakeTimersContext({ shouldAdvanceTime: true });
 *
 *   beforeEach(timers.setup);
 *   afterEach(timers.teardown);
 *
 *   test('debounced search', async () => {
 *     fireEvent.change(input, { target: { value: 'test' } });
 *     await act(async () => {
 *       vi.advanceTimersByTime(350);
 *       await vi.runAllTimersAsync();
 *     });
 *     expect(mockSearch).toHaveBeenCalled();
 *   });
 * });
 * ```
 */
export const createFakeTimersContext = (options: FakeTimersOptions = {}) => {
  return {
    setup: () => {
      const fakeTimerOptions: Parameters<typeof vi.useFakeTimers>[0] = {};
      // Copy defined option properties generically to handle future fields automatically
      for (const key of Object.keys(options) as (keyof FakeTimersOptions)[]) {
        const value = options[key];
        if (value !== undefined) {
          (fakeTimerOptions as Record<string, unknown>)[key] = value;
        }
      }
      vi.useFakeTimers(fakeTimerOptions);
    },
    teardown: () => {
      vi.runOnlyPendingTimers();
      vi.clearAllTimers();
      vi.useRealTimers();
    },
  };
};
