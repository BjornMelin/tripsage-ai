import { describe, expect, it, vi, beforeEach } from "vitest";

import { z } from "zod";

const mockGetCachedJson = vi.hoisted(() => vi.fn());
const mockSetCachedJson = vi.hoisted(() => vi.fn());
const mockRecordAgentToolEvent = vi.hoisted(() => vi.fn());
const mockGetRedis = vi.hoisted(() => vi.fn());
const mockRatelimitLimit = vi.hoisted(() => vi.fn());

vi.mock("@/lib/cache/upstash", () => ({
  getCachedJson: mockGetCachedJson,
  setCachedJson: mockSetCachedJson,
}));

vi.mock("@/lib/telemetry/agents", () => ({
  recordAgentToolEvent: mockRecordAgentToolEvent,
}));

vi.mock("@/lib/redis", () => ({
  getRedis: mockGetRedis,
}));

vi.mock("@upstash/ratelimit", () => {
  const limitFn = mockRatelimitLimit;
  const slidingWindow = vi.fn(() => ({}));
  const ctor = vi.fn(function RatelimitMock() {
    return { limit: limitFn };
  }) as unknown as {
    new (...args: unknown[]): { limit: ReturnType<typeof mockRatelimitLimit> };
    slidingWindow: (...args: unknown[]) => unknown;
  };
  ctor.slidingWindow = slidingWindow as unknown as (...args: unknown[]) => unknown;
  return {
    Ratelimit: ctor,
  };
});

import { runWithGuardrails } from "@/lib/agents";

describe("runWithGuardrails", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetCachedJson.mockResolvedValue(null);
    mockSetCachedJson.mockResolvedValue(undefined);
    mockRecordAgentToolEvent.mockResolvedValue(undefined);
    mockGetRedis.mockReturnValue(undefined);
    mockRatelimitLimit.mockResolvedValue({ success: true });
  });

  describe("validation", () => {
    it("validates input before executing", async () => {
      await expect(
        runWithGuardrails(
          {
            parametersSchema: z.object({ foo: z.string() }),
            tool: "demo",
            workflow: "destinationResearch",
          },
          { foo: 123 },
          async () => "ok"
        )
      ).rejects.toThrow();
    });

    it("passes through input when no schema provided", async () => {
      const execute = vi.fn().mockResolvedValue("ok");
      const { result } = await runWithGuardrails(
        {
          tool: "demo",
          workflow: "flightSearch",
        },
        { unvalidated: "data" },
        execute
      );
      expect(result).toBe("ok");
      expect(execute).toHaveBeenCalledWith({ unvalidated: "data" });
    });
  });

  describe("caching", () => {
    it("returns cached result when available", async () => {
      const cachedValue = { data: "cached" };
      mockGetCachedJson.mockResolvedValue(cachedValue);
      const execute = vi.fn();

      const { result, cacheHit } = await runWithGuardrails(
        {
          cache: {
            hashInput: false,
            key: "test:key",
            ttlSeconds: 60,
          },
          tool: "demo",
          workflow: "accommodationSearch",
        },
        { query: "test" },
        execute
      );

      expect(result).toEqual(cachedValue);
      expect(cacheHit).toBe(true);
      expect(execute).not.toHaveBeenCalled();
      expect(mockRecordAgentToolEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          cacheHit: true,
          durationMs: 0,
          status: "success",
        })
      );
    });

    it("caches result after execution", async () => {
      const executeResult = { data: "executed" };
      const execute = vi.fn().mockResolvedValue(executeResult);

      await runWithGuardrails(
        {
          cache: {
            hashInput: true,
            key: "test:cache",
            ttlSeconds: 300,
          },
          tool: "demo",
          workflow: "flightSearch",
        },
        { input: "test" },
        execute
      );

      expect(mockSetCachedJson).toHaveBeenCalledWith(
        expect.stringContaining("test:cache"),
        executeResult,
        300
      );
    });

    it("builds cache key with hash when hashInput is true", async () => {
      const execute = vi.fn().mockResolvedValue("result");
      await runWithGuardrails(
        {
          cache: {
            hashInput: true,
            key: "prefix",
            ttlSeconds: 60,
          },
          tool: "demo",
          workflow: "router",
        },
        { data: "test" },
        execute
      );

      const cacheKey = mockSetCachedJson.mock.calls[0]?.[0];
      expect(cacheKey).toMatch(/^prefix:[a-f0-9]{16}$/);
    });
  });

  describe("rate limiting", () => {
    it("enforces rate limit when Redis is available", async () => {
      mockRatelimitLimit.mockResolvedValue({ success: true });
      mockGetRedis.mockReturnValue({} as never);

      const execute = vi.fn().mockResolvedValue("ok");
      await runWithGuardrails(
        {
          rateLimit: {
            identifier: "user-123",
            limit: 10,
            window: "1 m",
          },
          tool: "demo",
          workflow: "flightSearch",
        },
        { input: "test" },
        execute
      );

      expect(mockRatelimitLimit).toHaveBeenCalled();
    });

    it("skips rate limiting when Redis is unavailable", async () => {
      mockGetRedis.mockReturnValue(undefined);
      const execute = vi.fn().mockResolvedValue("ok");

      await runWithGuardrails(
        {
          rateLimit: {
            identifier: "user-123",
            limit: 10,
            window: "1 m",
          },
          tool: "demo",
          workflow: "accommodationSearch",
        },
        { input: "test" },
        execute
      );

      expect(execute).toHaveBeenCalled();
    });

    it("throws error when rate limit is exceeded", async () => {
      mockRatelimitLimit.mockResolvedValue({ success: false });
      mockGetRedis.mockReturnValue({} as never);

      const execute = vi.fn();
      await expect(
        runWithGuardrails(
          {
            rateLimit: {
              identifier: "user-123",
              limit: 10,
              window: "1 m",
            },
            tool: "demo",
            workflow: "destinationResearch",
          },
          { input: "test" },
          execute
        )
      ).rejects.toThrow("Rate limit exceeded");
    });
  });

  describe("telemetry", () => {
    it("emits telemetry on success", async () => {
      const execute = vi.fn().mockResolvedValue({ ok: true });
      await runWithGuardrails(
        {
          parametersSchema: z.object({ v: z.number() }),
          tool: "demo",
          workflow: "router",
        },
        { v: 1 },
        execute
      );

      expect(mockRecordAgentToolEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          cacheHit: false,
          status: "success",
          tool: "demo",
          workflow: "router",
        })
      );
      const call = mockRecordAgentToolEvent.mock.calls[0]?.[0];
      expect(call?.durationMs).toBeGreaterThanOrEqual(0);
    });

    it("emits telemetry on error", async () => {
      const error = new Error("Execution failed");
      const execute = vi.fn().mockRejectedValue(error);

      await expect(
        runWithGuardrails(
          {
            tool: "demo",
            workflow: "flightSearch",
          },
          { input: "test" },
          execute
        )
      ).rejects.toThrow("Execution failed");

      expect(mockRecordAgentToolEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          cacheHit: false,
          errorMessage: "Execution failed",
          status: "error",
          tool: "demo",
          workflow: "flightSearch",
        })
      );
    });
  });

  describe("execution flow", () => {
    it("returns result when guardrails pass", async () => {
      const { result, cacheHit } = await runWithGuardrails(
        {
          parametersSchema: z.object({ foo: z.string() }),
          tool: "demo",
          workflow: "destinationResearch",
        },
        { foo: "bar" },
        async () => "ok"
      );
      expect(result).toBe("ok");
      expect(cacheHit).toBe(false);
    });

    it("propagates execution errors", async () => {
      const error = new Error("Tool execution failed");
      await expect(
        runWithGuardrails(
          {
            tool: "demo",
            workflow: "accommodationSearch",
          },
          { input: "test" },
          async () => {
            throw error;
          }
        )
      ).rejects.toThrow("Tool execution failed");
    });
  });
});
