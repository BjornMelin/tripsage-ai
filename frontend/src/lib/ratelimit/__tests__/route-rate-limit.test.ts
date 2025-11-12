import type { Redis } from "@upstash/redis";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { buildRouteRateLimiter, enforceRouteRateLimit } from "../config";

const mockSlidingWindow = vi.hoisted(() => vi.fn(() => ({})));
const mockLimitFn = vi.hoisted(() => vi.fn());

vi.mock("@upstash/ratelimit", () => {
  const slidingWindow = mockSlidingWindow;
  const limitFn = mockLimitFn;
  const ctor = vi.fn(function RatelimitMock() {
    return { limit: limitFn };
  }) as unknown as {
    new (...args: unknown[]): { limit: ReturnType<typeof mockLimitFn> };
    slidingWindow: (...args: unknown[]) => unknown;
  };
  ctor.slidingWindow = slidingWindow as unknown as (...args: unknown[]) => unknown;
  return {
    Ratelimit: ctor,
  };
});

describe("buildRouteRateLimiter", () => {
  const mockRedis = {} as Redis;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("creates Ratelimit instance with correct configuration", () => {
    buildRouteRateLimiter("flightSearch", mockRedis);

    expect(mockSlidingWindow).toHaveBeenCalledWith(30, "1 m");
  });

  it("uses correct limit for workflow", () => {
    buildRouteRateLimiter("accommodationSearch", mockRedis);

    expect(mockSlidingWindow).toHaveBeenCalledWith(30, "1 m");
  });

  it("throws error for unknown workflow", () => {
    expect(() => {
      buildRouteRateLimiter("unknown" as never, mockRedis);
    }).toThrow("Route rate limit configuration not found");
  });

  it("creates different limiters for different workflows", () => {
    buildRouteRateLimiter("flightSearch", mockRedis);
    buildRouteRateLimiter("accommodationSearch", mockRedis);

    expect(mockSlidingWindow).toHaveBeenCalledTimes(2);
  });
});

describe("enforceRouteRateLimit", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSlidingWindow.mockReturnValue({});
    vi.spyOn(console, "error").mockImplementation(() => {
      /* noop */
    });
  });

  it("returns null when Redis is unavailable", async () => {
    const getRedis = vi.fn().mockReturnValue(undefined);

    const result = await enforceRouteRateLimit("flightSearch", "user-123", getRedis);

    expect(result).toBeNull();
  });

  it("returns null when rate limit passes", async () => {
    mockLimitFn.mockResolvedValue({ success: true });
    const getRedis = vi.fn().mockReturnValue({} as Redis);

    const result = await enforceRouteRateLimit(
      "accommodationSearch",
      "user-456",
      getRedis
    );

    expect(result).toBeNull();
    expect(mockLimitFn).toHaveBeenCalled();
  });

  it("returns error response when rate limit exceeded", async () => {
    mockLimitFn.mockResolvedValue({ success: false });
    const getRedis = vi.fn().mockReturnValue({} as Redis);

    const result = await enforceRouteRateLimit("flightSearch", "user-789", getRedis);

    expect(result).toEqual({
      error: "rate_limit_exceeded",
      reason: "Too many requests",
      status: 429,
    });
    expect(mockLimitFn).toHaveBeenCalled();
  });

  it("gracefully degrades on rate limit errors", async () => {
    const error = new Error("Redis connection failed");
    const { Ratelimit } = await import("@upstash/ratelimit");
    vi.mocked(Ratelimit).mockImplementationOnce(() => {
      throw error;
    });
    const getRedis = vi.fn().mockReturnValue({} as Redis);

    const result = await enforceRouteRateLimit(
      "destinationResearch",
      "user-999",
      getRedis
    );

    expect(result).toBeNull();
    expect(console.error).toHaveBeenCalledWith(
      "Route rate limit enforcement error",
      expect.objectContaining({
        workflow: "destinationResearch",
      })
    );
  });

  it("handles all workflow types", async () => {
    mockLimitFn.mockResolvedValue({ success: true });
    const getRedis = vi.fn().mockReturnValue({} as Redis);

    const workflows = [
      "flightSearch",
      "accommodationSearch",
      "budgetPlanning",
      "destinationResearch",
      "itineraryPlanning",
      "memoryUpdate",
      "router",
    ] as const;

    for (const workflow of workflows) {
      const result = await enforceRouteRateLimit(workflow, "test-id", getRedis);
      expect(result).toBeNull();
    }
  });
});
