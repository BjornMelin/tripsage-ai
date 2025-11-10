/**
 * @fileoverview Centralized mock factories for tests.
 * Use these instead of global mocks in test-setup.ts for better test isolation and faster boot times.
 *
 * Usage:
 *   import { createMockStorage, createMockMatchMedia, createMockResizeObserver } from "@/test/mocks";
 *
 *   beforeEach(() => {
 *     const storage = createMockStorage({ token: "abc123" });
 *     window.localStorage = storage;
 *   });
 */

export * from "./media-query";
export * from "./observers";
export * from "./storage";
