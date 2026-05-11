/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

const redisRef = vi.hoisted<{ current: unknown | undefined }>(() => ({
  current: {},
}));
const constructorMock = vi.hoisted(() => vi.fn());
const limitMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/redis", () => ({
  getRedis: () => redisRef.current,
}));

vi.mock("@upstash/ratelimit", () => {
  class Ratelimit {
    static slidingWindow(tokens: number, window: string) {
      return { tokens, window };
    }

    constructor(options: unknown) {
      constructorMock(options);
    }

    limit(identifier: string) {
      return limitMock(identifier);
    }
  }

  return { Ratelimit };
});

async function loadModule() {
  const mod = await import("../upstash");
  mod.resetUpstashRateLimiterCacheForTests();
  return mod;
}

describe("checkUpstashRateLimit", () => {
  beforeEach(() => {
    vi.resetModules();
    redisRef.current = {};
    constructorMock.mockReset();
    limitMock.mockReset();
    limitMock.mockResolvedValue({
      limit: 10,
      pending: Promise.resolve(),
      remaining: 9,
      reset: Date.now() + 60_000,
      success: true,
    });
  });

  it("reports unavailable when Redis is not configured", async () => {
    redisRef.current = undefined;
    const { checkUpstashRateLimit } = await loadModule();

    await expect(
      checkUpstashRateLimit({
        identifier: "ip:unknown",
        limit: 10,
        prefix: "ratelimit:test",
        window: "1 m",
      })
    ).resolves.toEqual({
      reason: "redis_unavailable",
      status: "unavailable",
    });

    expect(constructorMock).not.toHaveBeenCalled();
  });

  it("maps Upstash timeout results to unavailable", async () => {
    limitMock.mockResolvedValue({
      limit: 10,
      pending: Promise.resolve(),
      reason: "timeout",
      remaining: 10,
      reset: Date.now() + 60_000,
      success: true,
    });
    const { checkUpstashRateLimit } = await loadModule();

    const result = await checkUpstashRateLimit({
      identifier: "user:123",
      limit: 10,
      prefix: "ratelimit:test",
      window: "1 m",
    });

    expect(result).toMatchObject({
      reason: "timeout",
      status: "unavailable",
    });
  });

  it("returns limited results without applying surface policy", async () => {
    limitMock.mockResolvedValue({
      limit: 2,
      pending: Promise.resolve(),
      reason: "cacheBlock",
      remaining: 0,
      reset: Date.now() + 60_000,
      success: false,
    });
    const { checkUpstashRateLimit } = await loadModule();

    const result = await checkUpstashRateLimit({
      identifier: "user:123",
      limit: 2,
      prefix: "ratelimit:test",
      window: "1 m",
    });

    expect(result).toMatchObject({
      result: { limit: 2, reason: "cacheBlock", remaining: 0, success: false },
      status: "limited",
    });
  });

  it("caches equivalent limiter definitions", async () => {
    const { checkUpstashRateLimit } = await loadModule();
    const options = {
      analytics: true,
      dynamicLimits: true,
      ephemeralCache: false as const,
      identifier: "user:123",
      limit: 10,
      prefix: "ratelimit:test",
      window: "1 m",
    };

    await checkUpstashRateLimit(options);
    await checkUpstashRateLimit(options);

    expect(constructorMock).toHaveBeenCalledTimes(1);
  });
});
