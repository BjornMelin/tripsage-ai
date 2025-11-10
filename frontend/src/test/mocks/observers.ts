/**
 * @fileoverview Observer API mocks (ResizeObserver, IntersectionObserver) for tests.
 * Use these instead of global mocks to improve test boot time.
 *
 * Usage:
 *   import { createMockResizeObserver, installMockObservers } from "@/test/mocks/observers";
 *
 *   it("should observe element resize", () => {
 *     const observer = createMockResizeObserver();
 *     observer.observe(element);
 *     expect(observer.observe).toHaveBeenCalledWith(element);
 *   });
 */

import { vi } from "vitest";

/**
 * Creates a mock ResizeObserver with spy functions.
 *
 * @param callback - Optional callback to invoke on observe
 * @returns A ResizeObserver-compatible mock
 */
export const createMockResizeObserver = (
  callback?: ResizeObserverCallback
): ResizeObserver => {
  class MockResizeObserver implements ResizeObserver {
    observe = vi.fn((target: Element) => {
      if (callback) {
        const entries: ResizeObserverEntry[] = [
          {
            borderBoxSize: [],
            contentBoxSize: [],
            contentRect: target.getBoundingClientRect(),
            devicePixelContentBoxSize: [],
            target,
          },
        ];
        callback(entries, this);
      }
    });

    unobserve = vi.fn();
    disconnect = vi.fn();
  }

  return new MockResizeObserver();
};

/**
 * Creates a mock IntersectionObserver with spy functions.
 *
 * @param callback - Optional callback to invoke on observe
 * @param options - Optional IntersectionObserver options
 * @returns An IntersectionObserver-compatible mock
 */
export const createMockIntersectionObserver = (
  callback?: IntersectionObserverCallback,
  options?: IntersectionObserverInit
): IntersectionObserver => {
  class MockIntersectionObserver implements IntersectionObserver {
    readonly root: Element | Document | null = options?.root ?? null;
    readonly rootMargin = options?.rootMargin ?? "";
    readonly thresholds: number[] = Array.isArray(options?.threshold)
      ? options.threshold
      : options?.threshold !== undefined
        ? [options.threshold]
        : [];

    observe = vi.fn((target: Element) => {
      if (callback) {
        const entries: IntersectionObserverEntry[] = [
          {
            boundingClientRect: target.getBoundingClientRect(),
            intersectionRatio: 1,
            intersectionRect: target.getBoundingClientRect(),
            isIntersecting: true,
            rootBounds: null,
            target,
            time: Date.now(),
          },
        ];
        callback(entries, this);
      }
    });

    unobserve = vi.fn();
    disconnect = vi.fn();
    takeRecords = vi.fn(() => []);
  }

  return new MockIntersectionObserver();
};

/**
 * Installs mock observers on the global scope for tests.
 * Use sparingly - prefer createMock* functions for better isolation.
 *
 * @example
 * beforeEach(() => {
 *   installMockObservers();
 * });
 */
export const installMockObservers = (): void => {
  (globalThis as { ResizeObserver: typeof ResizeObserver }).ResizeObserver =
    createMockResizeObserver as unknown as typeof ResizeObserver;

  (
    globalThis as { IntersectionObserver: typeof IntersectionObserver }
  ).IntersectionObserver =
    createMockIntersectionObserver as unknown as typeof IntersectionObserver;
};
