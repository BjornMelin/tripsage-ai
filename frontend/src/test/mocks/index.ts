/**
 * @fileoverview Test mocks barrel.
 *
 * Exception to barrel export policy: Test infrastructure
 * uses barrel exports for convenience in test setup files.
 *
 * Usage:
 *   import { createMockStorage, createMockMatchMedia, createMockResizeObserver } from "@/test/mocks";
 *
 *   beforeEach(() => {
 *     const storage = createMockStorage({ token: "abc123" });
 *     window.localStorage = storage;
 *   });
 */

export * from "./cache";
export * from "./media-query";
export * from "./observers";
export * from "./storage";
