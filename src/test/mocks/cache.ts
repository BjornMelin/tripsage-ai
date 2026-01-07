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
  getCachedJsonSafe: ReturnType<typeof vi.fn>;
  setCachedJson: ReturnType<typeof vi.fn>;
  deleteCachedJson: ReturnType<typeof vi.fn>;
  deleteCachedJsonMany: ReturnType<typeof vi.fn>;
  reset: () => void;
  module: {
    getCachedJson: UpstashCacheMock["getCachedJson"];
    getCachedJsonSafe: UpstashCacheMock["getCachedJsonSafe"];
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

  const getCachedJsonSafe = vi.fn(
    async <T>(
      key: string,
      schema?: {
        safeParse: (
          value: unknown
        ) => { success: boolean; data: T } | { success: false };
      }
    ) => {
      await Promise.resolve();
      const raw = store.get(key);
      if (!raw) return { status: "miss" as const };

      let parsed: unknown;
      try {
        parsed = JSON.parse(raw);
      } catch {
        return { raw, status: "invalid" as const };
      }

      if (schema) {
        const result = schema.safeParse(parsed);
        if (!result.success) {
          return { raw: parsed, status: "invalid" as const };
        }
        return { data: result.data, status: "hit" as const };
      }

      return { data: parsed as T, status: "hit" as const };
    }
  );

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
    getCachedJsonSafe.mockClear();
    setCachedJson.mockClear();
    deleteCachedJson.mockClear();
    deleteCachedJsonMany.mockClear();
  };

  return {
    deleteCachedJson,
    deleteCachedJsonMany,
    getCachedJson,
    getCachedJsonSafe,
    module: {
      __reset: reset,
      deleteCachedJson,
      deleteCachedJsonMany,
      getCachedJson,
      getCachedJsonSafe,
      setCachedJson,
    },
    reset,
    setCachedJson,
    store,
  };
}

/**
 * Convenience helper for hoisted Upstash cache mocks in vitest.
 *
 * Usage:
 *   const { cache, factory } = hoistedUpstashMock();
 *   vi.mock("@/lib/cache/upstash", factory);
 *   beforeEach(() => cache.reset());
 */
export function hoistedUpstashMock(): {
  cache: UpstashCacheMock;
  factory: () => UpstashCacheMock["module"];
} {
  const cache = vi.hoisted(() => buildUpstashCacheMock());
  return {
    cache,
    factory: () => cache.module,
  };
}
