/** @vitest-environment jsdom */

import { TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import type { ToolCallOptions } from "ai";
import { afterAll, beforeAll, beforeEach, describe, expect, test, vi } from "vitest";
import { z } from "zod";
import { setupUpstashTestEnvironment } from "@/test/upstash/setup";

const headerStore = new Map<string, string>();
const setMockHeaders = (values: Record<string, string | undefined>) => {
  headerStore.clear();
  for (const [key, value] of Object.entries(values)) {
    if (typeof value === "string") {
      headerStore.set(key.toLowerCase(), value);
    }
  }
};

const telemetrySpan = {
  addEvent: vi.fn(),
  setAttribute: vi.fn(),
};

const {
  deleteCachedJson,
  deleteCachedJsonMany,
  getCachedJson,
  getUpstashCache,
  setCachedJson,
} = vi.hoisted(() => {
  const upstashCacheStore = new Map<string, string>();
  const getCachedJsonFn = vi.fn(<T>(key: string): Promise<T | null> => {
    const raw = upstashCacheStore.get(key);
    if (!raw) return Promise.resolve(null);
    try {
      return Promise.resolve(JSON.parse(raw) as T);
    } catch {
      return Promise.resolve(null);
    }
  });
  const setCachedJsonFn = vi.fn((key: string, value: unknown): Promise<void> => {
    upstashCacheStore.set(key, JSON.stringify(value));
    return Promise.resolve();
  });
  const deleteCachedJsonFn = vi.fn((key: string): Promise<void> => {
    upstashCacheStore.delete(key);
    return Promise.resolve();
  });
  const deleteCachedJsonManyFn = vi.fn((keys: string[]): Promise<number> => {
    let deleted = 0;
    for (const key of keys) {
      if (upstashCacheStore.delete(key)) deleted += 1;
    }
    return Promise.resolve(deleted);
  });
  const resetUpstashCache = () => {
    upstashCacheStore.clear();
    getCachedJsonFn.mockClear();
    setCachedJsonFn.mockClear();
    deleteCachedJsonFn.mockClear();
    deleteCachedJsonManyFn.mockClear();
  };
  const getUpstashCacheFn = () => ({
    reset: resetUpstashCache,
    store: upstashCacheStore,
  });
  return {
    deleteCachedJson: deleteCachedJsonFn,
    deleteCachedJsonMany: deleteCachedJsonManyFn,
    getCachedJson: getCachedJsonFn,
    getUpstashCache: getUpstashCacheFn,
    setCachedJson: setCachedJsonFn,
  };
});

const redisClient = {
  get: vi.fn(),
  set: vi.fn(),
};

const {
  afterAllHook: upstashAfterAllHook,
  beforeEachHook: upstashBeforeEachHook,
  mocks: upstashMocks,
} = setupUpstashTestEnvironment();

const originalRatelimitLimit = upstashMocks.ratelimit.Ratelimit.prototype.limit;
const recordedRateLimitIdentifiers: string[] = [];

vi.mock("next/headers", () => ({
  headers: () =>
    Promise.resolve({
      get: (key: string) => headerStore.get(key.toLowerCase()) ?? null,
    }),
}));

vi.mock("@/lib/telemetry/span", () => ({
  recordTelemetryEvent: vi.fn(),
  sanitizeAttributes: (attrs: unknown) => attrs,
  withTelemetrySpan: (
    _name: string,
    _opts: unknown,
    execute: (span: typeof telemetrySpan) => Promise<unknown>
  ) => execute(telemetrySpan),
}));

vi.mock("@/lib/cache/upstash", () => ({
  deleteCachedJson,
  deleteCachedJsonMany,
  getCachedJson,
  setCachedJson,
}));

vi.mock("@/lib/redis", () => ({
  getRedis: () => redisClient,
}));

let createAiTool: typeof import("@ai/lib/tool-factory").createAiTool;

beforeAll(async () => {
  vi.resetModules();
  ({ createAiTool } = await import("@ai/lib/tool-factory"));
});

beforeEach(() => {
  upstashBeforeEachHook();
  getUpstashCache().reset();
  recordedRateLimitIdentifiers.length = 0;
  // Wrap limiter to capture identifiers while preserving mock behavior
  upstashMocks.ratelimit.Ratelimit.prototype.limit = vi.fn(function (
    this: InstanceType<(typeof upstashMocks.ratelimit)["Ratelimit"]>,
    identifier: string
  ) {
    recordedRateLimitIdentifiers.push(identifier);
    return originalRatelimitLimit.call(this, identifier);
  });
  telemetrySpan.addEvent.mockClear();
  telemetrySpan.setAttribute.mockClear();
  setMockHeaders({});
});

afterAll(upstashAfterAllHook);

describe("createAiTool", () => {
  test("creates AI SDK compatible tool with caching", async () => {
    const executeSpy = vi.fn(async ({ id }: { id: string }) => ({
      fromCache: false,
      id,
    }));

    const cachedTool = createAiTool({
      description: "cached tool for testing",
      execute: executeSpy,
      guardrails: {
        cache: {
          hashInput: false,
          key: ({ id }) => id,
          namespace: "tool:test:cache",
          onHit: (cached, _params, _meta) => ({ ...cached, fromCache: true }),
          ttlSeconds: 60,
        },
      },
      inputSchema: z.object({ id: z.string() }),
      name: "cachedTool",
    });

    // Test tool execution directly (unit test)
    const callOptions: ToolCallOptions = {
      messages: [],
      toolCallId: "test-call-1",
    };

    // First call - should execute and cache
    const firstResult = await cachedTool.execute?.({ id: "abc" }, callOptions);
    expect(firstResult).toEqual({ fromCache: false, id: "abc" });
    expect(executeSpy).toHaveBeenCalledTimes(1);
    // Verify cache was written
    expect(getUpstashCache().store.size).toBeGreaterThan(0);

    // Set up cache hit for second call - need to check actual cache key
    // The cache key is: namespace + ":" + key(params)
    // namespace defaults to `tool:${toolName}` if not provided, or uses cache.namespace
    // So it should be "tool:test:cache:abc" (namespace:tool:test:cache, key:abc)
    const cachedValue = { fromCache: false, id: "abc" };
    // Check what key was actually used in first call by inspecting cache store
    const cacheKeys = Array.from(getUpstashCache().store.keys());
    expect(cacheKeys.length).toBeGreaterThan(0);
    const actualCacheKey = cacheKeys[0];
    getUpstashCache().store.set(actualCacheKey, JSON.stringify(cachedValue));
    executeSpy.mockClear();

    // Second call - should use cache
    const secondResult = await cachedTool.execute?.({ id: "abc" }, callOptions);
    expect(secondResult).toEqual({ fromCache: true, id: "abc" });
    expect(executeSpy).not.toHaveBeenCalled();

    // Verify tool has AI SDK Tool structure
    expect(cachedTool).toHaveProperty("description");
    expect(cachedTool).toHaveProperty("execute");
    expect(cachedTool).toHaveProperty("inputSchema");
  });

  test("throws tool error when rate limit exceeded", async () => {
    upstashMocks.ratelimit.__force({
      limit: 1,
      remaining: 0,
      reset: Date.now() + 60_000,
      success: false,
    });

    const limitedTool = createAiTool({
      description: "limited tool for testing",
      execute: async () => ({ ok: true }),
      guardrails: {
        rateLimit: {
          errorCode: TOOL_ERROR_CODES.webSearchRateLimited,
          identifier: ({ id }: { id: string }) => `user-${id}`,
          limit: 1,
          prefix: "ratelimit:test",
          window: "1 m",
        },
      },
      inputSchema: z.object({ id: z.string() }),
      name: "limitedTool",
    });

    const callOptions: ToolCallOptions = {
      messages: [],
      toolCallId: "test-call-limited",
    };

    await expect(limitedTool.execute?.({ id: "1" }, callOptions)).rejects.toMatchObject(
      {
        code: TOOL_ERROR_CODES.webSearchRateLimited,
      }
    );
    expect(recordedRateLimitIdentifiers.length).toBeGreaterThan(0);
  });

  test("passes ToolCallOptions to execute function", async () => {
    let capturedCallOptions: ToolCallOptions | null = null;
    // biome-ignore lint/suspicious/useAwait: Mock function must return Promise to match tool execute signature
    const executeSpy = vi.fn(async (_params: unknown, callOptions: ToolCallOptions) => {
      capturedCallOptions = callOptions;
      return { result: "ok" };
    });

    const toolWithContext = createAiTool({
      description: "tool that uses context",
      execute: executeSpy,
      guardrails: {
        rateLimit: {
          errorCode: TOOL_ERROR_CODES.webSearchRateLimited,
          identifier: (_params, callOptions) => {
            // Test that callOptions.messages is available
            expect(callOptions?.messages).toBeDefined();
            expect(callOptions?.toolCallId).toBeDefined();
            return "test-identifier";
          },
          limit: 10,
          prefix: "ratelimit:test",
          window: "1 m",
        },
      },
      inputSchema: z.object({ query: z.string() }),
      name: "contextTool",
    });

    const callOptions: ToolCallOptions = {
      messages: [{ content: "test message", role: "user" }],
      toolCallId: "call-ctx-test",
    };

    // Rate limit will pass (success: true), so tool should execute
    await toolWithContext.execute?.({ query: "test" }, callOptions);

    expect(executeSpy).toHaveBeenCalled();
    expect(capturedCallOptions).toBeDefined();
    expect(capturedCallOptions).toHaveProperty("toolCallId", "call-ctx-test");
    expect(capturedCallOptions).toHaveProperty("messages");
    const options = capturedCallOptions as ToolCallOptions | null;
    expect(options?.messages).toHaveLength(1);
  });

  test("prefers x-user-id header when deriving rate-limit identifier", async () => {
    setMockHeaders({
      "x-forwarded-for": "203.0.113.10, 203.0.113.11",
      "x-user-id": "user-abc",
    });

    const tool = createAiTool({
      description: "rate limited tool",
      execute: async () => ({ ok: true }),
      guardrails: {
        rateLimit: {
          errorCode: TOOL_ERROR_CODES.toolRateLimited,
          limit: 5,
          window: "1 m",
        },
      },
      inputSchema: z.object({ payload: z.string() }),
      name: "headerTool",
    });

    await tool.execute?.({ payload: "demo" }, { messages: [], toolCallId: "call-1" });
    expect(recordedRateLimitIdentifiers).toContain(
      "user:291fd0e83dac217f4e5bd62d007d2c754e061a92f76b0d7468be3544f95c28cd"
    );
  });

  test("falls back to x-forwarded-for header when user header missing", async () => {
    setMockHeaders({
      "x-forwarded-for": "198.51.100.25, 198.51.100.26",
    });

    const tool = createAiTool({
      description: "rate limited tool fallback",
      execute: async () => ({ ok: true }),
      guardrails: {
        rateLimit: {
          errorCode: TOOL_ERROR_CODES.toolRateLimited,
          limit: 3,
          window: "1 m",
        },
      },
      inputSchema: z.object({ payload: z.string() }),
      name: "headerToolFallback",
    });

    await tool.execute?.({ payload: "demo" }, { messages: [], toolCallId: "call-2" });
    expect(recordedRateLimitIdentifiers).toContain(
      "ip:725adbffa67a0230fdf009da59ec27b10093cc3b2cb5b9fe72868c0d571b7ad8"
    );
  });

  test("defaults to unknown identifier when headers missing", async () => {
    setMockHeaders({});

    const tool = createAiTool({
      description: "rate limited tool default",
      execute: async () => ({ ok: true }),
      guardrails: {
        rateLimit: {
          errorCode: TOOL_ERROR_CODES.toolRateLimited,
          limit: 2,
          window: "1 m",
        },
      },
      inputSchema: z.object({ payload: z.string() }),
      name: "headerToolUnknown",
    });

    await tool.execute?.({ payload: "demo" }, { messages: [], toolCallId: "call-3" });
    expect(recordedRateLimitIdentifiers).toContain("ip:unknown");
  });

  test("rejects invalid x-forwarded-for IP addresses to prevent spoofing", async () => {
    setMockHeaders({
      "x-forwarded-for": "not-an-ip-address, 198.51.100.25",
    });

    const tool = createAiTool({
      description: "rate limited tool with invalid IP",
      execute: async () => ({ ok: true }),
      guardrails: {
        rateLimit: {
          errorCode: TOOL_ERROR_CODES.toolRateLimited,
          limit: 2,
          window: "1 m",
        },
      },
      inputSchema: z.object({ payload: z.string() }),
      name: "headerToolInvalidIp",
    });

    // Should fall back to "unknown" when IP is invalid
    await tool.execute?.({ payload: "demo" }, { messages: [], toolCallId: "call-4" });
    expect(recordedRateLimitIdentifiers).toContain("ip:unknown");
  });
});
