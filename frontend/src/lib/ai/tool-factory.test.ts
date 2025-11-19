/** @vitest-environment jsdom */

import type { ToolCallOptions } from "ai";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { z } from "zod";

import { createAiTool } from "@/lib/ai/tool-factory";
import { TOOL_ERROR_CODES } from "@/lib/tools/errors";

const headerStore = new Map<string, string>();

const setMockHeaders = (values: Record<string, string | undefined>) => {
  headerStore.clear();
  for (const [key, value] of Object.entries(values)) {
    if (typeof value === "string") {
      headerStore.set(key.toLowerCase(), value);
    }
  }
};

vi.mock("next/headers", () => ({
  headers: () =>
    Promise.resolve({
      get: (key: string) => headerStore.get(key.toLowerCase()) ?? null,
    }),
}));

const telemetrySpan = {
  addEvent: vi.fn(),
  setAttribute: vi.fn(),
};

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: (
    _name: string,
    _opts: unknown,
    execute: (span: typeof telemetrySpan) => Promise<unknown>
  ) => execute(telemetrySpan),
}));

const cacheStorage = new Map<string, unknown>();

vi.mock("@/lib/cache/upstash", () => ({
  // biome-ignore lint/suspicious/useAwait: Mock functions must return Promises to match real API
  getCachedJson: vi.fn(async <T>(key: string): Promise<T | null> => {
    return (cacheStorage.get(key) as T) ?? null;
  }),
  // biome-ignore lint/suspicious/useAwait: Mock functions must return Promises to match real API
  setCachedJson: vi.fn(async (key: string, value: unknown): Promise<void> => {
    cacheStorage.set(key, value);
  }),
}));

const redisClient = {
  get: vi.fn(),
  set: vi.fn(),
};

vi.mock("@/lib/redis", () => ({
  getRedis: () => redisClient,
}));

const ratelimitLimit = vi.fn(
  async (): Promise<{
    success: boolean;
    limit?: number;
    remaining?: number;
    reset?: number;
  }> => ({ success: true })
);

vi.mock("@upstash/ratelimit", () => ({
  Ratelimit: class {
    static slidingWindow(limit: number, window: string) {
      return { limit, window };
    }

    limit = ratelimitLimit;
  },
}));

// Removed unused baseCallOptions - each test creates its own callOptions

beforeEach(() => {
  cacheStorage.clear();
  ratelimitLimit.mockClear();
  telemetrySpan.addEvent.mockClear();
  telemetrySpan.setAttribute.mockClear();
  setMockHeaders({});
});

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
    expect(cacheStorage.size).toBeGreaterThan(0);

    // Set up cache hit for second call - need to check actual cache key
    // The cache key is: namespace + ":" + key(params)
    // namespace defaults to `tool:${toolName}` if not provided, or uses cache.namespace
    // So it should be "tool:test:cache:abc" (namespace:tool:test:cache, key:abc)
    const cachedValue = { fromCache: false, id: "abc" };
    // Check what key was actually used in first call by inspecting cacheStorage
    const cacheKeys = Array.from(cacheStorage.keys());
    expect(cacheKeys.length).toBeGreaterThan(0);
    const actualCacheKey = cacheKeys[0];
    cacheStorage.set(actualCacheKey, cachedValue);
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
    ratelimitLimit.mockResolvedValue({
      limit: 1,
      remaining: 0,
      reset: Math.floor(Date.now() / 1000) + 60,
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
    expect(ratelimitLimit).toHaveBeenCalled();
  });

  test("passes ToolCallOptions to execute function", async () => {
    // Ensure rate limit passes for this test
    ratelimitLimit.mockResolvedValueOnce({
      limit: 10,
      remaining: 9,
      success: true,
    });

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
    ratelimitLimit.mockResolvedValue({
      limit: 5,
      remaining: 4,
      success: true,
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
    expect(ratelimitLimit).toHaveBeenCalledWith("user:user-abc");
  });

  test("falls back to x-forwarded-for header when user header missing", async () => {
    setMockHeaders({
      "x-forwarded-for": "198.51.100.25, 198.51.100.26",
    });
    ratelimitLimit.mockResolvedValue({
      limit: 3,
      remaining: 2,
      success: true,
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
    expect(ratelimitLimit).toHaveBeenCalledWith("ip:198.51.100.25");
  });

  test("defaults to unknown identifier when headers missing", async () => {
    setMockHeaders({});
    ratelimitLimit.mockResolvedValue({
      limit: 2,
      remaining: 1,
      success: true,
    });

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
    expect(ratelimitLimit).toHaveBeenCalledWith("unknown");
  });

  test("rejects invalid x-forwarded-for IP addresses to prevent spoofing", async () => {
    setMockHeaders({
      "x-forwarded-for": "not-an-ip-address, 198.51.100.25",
    });
    ratelimitLimit.mockResolvedValue({
      limit: 2,
      remaining: 1,
      success: true,
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
    expect(ratelimitLimit).toHaveBeenCalledWith("unknown");
  });
});
