/**
 * @fileoverview Storage mock factory for tests that need localStorage/sessionStorage.
 * Use this instead of global mocks to improve test boot time.
 *
 * Usage:
 *   import { createMockStorage } from "@/test/mocks/storage";
 *
 *   it("should save to storage", () => {
 *     const storage = createMockStorage();
 *     storage.setItem("key", "value");
 *     expect(storage.getItem("key")).toBe("value");
 *   });
 */

import { vi } from "vitest";

/**
 * Creates a mock Storage implementation backed by a Map.
 * Fully implements the Web Storage API with Vitest spies.
 *
 * @param initialData - Optional initial key-value pairs
 * @returns A Storage-compatible mock object with spy functions
 */
export const createMockStorage = (initialData?: Record<string, string>): Storage => {
  const store = new Map<string, string>(Object.entries(initialData ?? {}));

  return {
    clear: vi.fn(() => store.clear()),
    getItem: vi.fn((key: string) => store.get(key) ?? null),
    key: vi.fn((index: number) => Array.from(store.keys())[index] ?? null),
    get length() {
      return store.size;
    },
    removeItem: vi.fn((key: string) => {
      store.delete(key);
    }),
    setItem: vi.fn((key: string, value: string) => {
      store.set(key, value);
    }),
  };
};

/**
 * Installs the mock storage on window for tests that expect global access.
 *
 * @param type - "localStorage" or "sessionStorage"
 * @param initialData - Optional initial data
 * @returns The mock storage instance
 *
 * @example
 * beforeEach(() => {
 *   installMockStorage("localStorage", { token: "abc123" });
 * });
 */
export const installMockStorage = (
  type: "localStorage" | "sessionStorage",
  initialData?: Record<string, string>
): Storage => {
  const mockStorage = createMockStorage(initialData);
  Object.defineProperty(window, type, {
    configurable: true,
    value: mockStorage,
    writable: true,
  });
  return mockStorage;
};
