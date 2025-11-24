/**
 * @fileoverview Shared Upstash cache mock helpers for tests.
 *
 * Provides an in-memory implementation matching the `@/lib/cache/upstash`
 * surface (getCachedJson, setCachedJson, deleteCachedJson, deleteCachedJsonMany).
 * Use per-suite instances to avoid cross-test leakage and keep hoisted vi.mock
 * factories simple.
 */

import { vi } from "vitest";

export type UpstashCacheMock = {
  store: Map<string, string>;
  getCachedJson: ReturnType<typeof vi.fn>;
  setCachedJson: ReturnType<typeof vi.fn>;
  deleteCachedJson: ReturnType<typeof vi.fn>;
  deleteCachedJsonMany: ReturnType<typeof vi.fn>;
  reset: () => void;
  module: {
    getCachedJson: UpstashCacheMock["getCachedJson"];
    setCachedJson: UpstashCacheMock["setCachedJson"];
    deleteCachedJson: UpstashCacheMock["deleteCachedJson"];
    deleteCachedJsonMany: UpstashCacheMock["deleteCachedJsonMany"];
    __reset: UpstashCacheMock["reset"];
  };
};

/**
 * Build a fresh Upstash cache mock instance.
 *
 * Example:
 *   const upstash = buildUpstashCacheMock();
 *   vi.mock("@/lib/cache/upstash", () => upstash.module);
 *   beforeEach(() => upstash.reset());
 */
export function buildUpstashCacheMock(): UpstashCacheMock {
  const store = new Map<string, string>();

  const getCachedJson = vi.fn(<T>(key: string): Promise<T | null> => {
    const raw = store.get(key);
    if (!raw) return Promise.resolve(null);
    try {
      return Promise.resolve(JSON.parse(raw) as T);
    } catch {
      return Promise.resolve(null);
    }
  });

  const setCachedJson = vi.fn((key: string, value: unknown): Promise<void> => {
    store.set(key, JSON.stringify(value));
    return Promise.resolve();
  });

  const deleteCachedJson = vi.fn((key: string): Promise<void> => {
    store.delete(key);
    return Promise.resolve();
  });

  const deleteCachedJsonMany = vi.fn((keys: string[]): Promise<number> => {
    let deleted = 0;
    for (const key of keys) {
      if (store.delete(key)) deleted += 1;
    }
    return Promise.resolve(deleted);
  });

  const reset = (): void => {
    store.clear();
    getCachedJson.mockClear();
    setCachedJson.mockClear();
    deleteCachedJson.mockClear();
    deleteCachedJsonMany.mockClear();
  };

  return {
    deleteCachedJson,
    deleteCachedJsonMany,
    getCachedJson,
    module: {
      __reset: reset,
      deleteCachedJson,
      deleteCachedJsonMany,
      getCachedJson,
      setCachedJson,
    },
    reset,
    setCachedJson,
    store,
  };
}
