import type { ToolCallOptions } from "ai";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { z } from "zod";

import { createAiTool } from "@/lib/ai/tool-factory";
import { TOOL_ERROR_CODES } from "@/lib/tools/errors";

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

const redisStorage = new Map<string, string>();
const redisClient = {
  get: vi.fn(async (key: string) => redisStorage.get(key) ?? null),
  set: vi.fn((key: string, value: string, opts?: { ex?: number }) => {
    redisStorage.set(key, value);
    return Promise.resolve(opts);
  }),
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

const baseCallOptions: ToolCallOptions = {
  messages: [],
  toolCallId: "test-call",
};

beforeEach(() => {
  redisStorage.clear();
  redisClient.get.mockClear();
  redisClient.set.mockClear();
  ratelimitLimit.mockClear();
  telemetrySpan.addEvent.mockClear();
  telemetrySpan.setAttribute.mockClear();
});

describe("createAiTool", () => {
  test("caches successful results", async () => {
    const executeSpy = vi.fn(async ({ id }: { id: string }) => ({
      fromCache: false,
      id,
    }));

    const cachedTool = createAiTool({
      description: "cached",
      execute: executeSpy,
      guardrails: {
        cache: {
          key: ({ id }) => id,
          namespace: "tool:test:cache",
          onHit: (cached, _params, _meta) => ({ ...cached, fromCache: true }),
          ttlSeconds: 60,
        },
      },
      inputSchema: z.object({ id: z.string() }),
      name: "cachedTool",
    });

    const first = await cachedTool.execute?.({ id: "abc" }, baseCallOptions);
    expect(first).toEqual({ fromCache: false, id: "abc" });
    expect(executeSpy).toHaveBeenCalledTimes(1);

    const second = await cachedTool.execute?.({ id: "abc" }, baseCallOptions);
    expect(second).toEqual({ fromCache: true, id: "abc" });
    expect(executeSpy).toHaveBeenCalledTimes(1);
    expect(redisClient.get).toHaveBeenCalled();
    expect(redisClient.set).toHaveBeenCalled();
  });

  test("throws tool error when rate limit exceeded", async () => {
    ratelimitLimit.mockResolvedValueOnce({
      limit: 1,
      remaining: 0,
      reset: Math.floor(Date.now() / 1000) + 60,
      success: false,
    });

    const limitedTool = createAiTool({
      description: "limited",
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

    const limitedExecution = limitedTool.execute?.({ id: "1" }, baseCallOptions);
    await expect(limitedExecution).rejects.toMatchObject({
      code: TOOL_ERROR_CODES.webSearchRateLimited,
    });
    expect(ratelimitLimit).toHaveBeenCalled();
  });
});
