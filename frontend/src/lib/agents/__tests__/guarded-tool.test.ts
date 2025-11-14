import { beforeEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";
import { buildGuardedTool } from "../guarded-tool";
import * as runtime from "../runtime";

vi.mock("../runtime");

describe("buildGuardedTool", () => {
  const mockRunWithGuardrails = vi.spyOn(runtime, "runWithGuardrails");

  beforeEach(() => {
    vi.clearAllMocks();
    mockRunWithGuardrails.mockResolvedValue({
      cacheHit: false,
      result: "test-result",
    });
  });

  it("wraps tool execution with guardrails", async () => {
    const schema = z.object({ foo: z.string() });
    const execute = vi.fn().mockResolvedValue("executed");

    const guarded = buildGuardedTool({
      execute,
      schema,
      toolKey: "testTool",
      workflow: "flightSearch",
    });

    const result = await guarded({ foo: "bar" });

    expect(result).toBe("test-result");
    expect(mockRunWithGuardrails).toHaveBeenCalledWith(
      {
        cache: undefined,
        parametersSchema: schema,
        rateLimit: undefined,
        tool: "testTool",
        workflow: "flightSearch",
      },
      { foo: "bar" },
      execute
    );
  });

  it("passes cache configuration to guardrails", async () => {
    const schema = z.object({ id: z.number() });
    const execute = vi.fn().mockResolvedValue({ data: "test" });
    const cache = {
      hashInput: true,
      key: "test:cache",
      ttlSeconds: 300,
    };

    const guarded = buildGuardedTool({
      cache,
      execute,
      schema,
      toolKey: "cachedTool",
      workflow: "accommodationSearch",
    });

    await guarded({ id: 123 });

    expect(mockRunWithGuardrails).toHaveBeenCalledWith(
      expect.objectContaining({
        cache,
      }),
      { id: 123 },
      execute
    );
  });

  it("passes rate limit configuration to guardrails", async () => {
    const schema = z.object({ query: z.string() });
    const execute = vi.fn().mockResolvedValue({ results: [] });
    const rateLimit = {
      identifier: "user-123",
      limit: 10,
      window: "1 m",
    };

    const guarded = buildGuardedTool({
      execute,
      rateLimit,
      schema,
      toolKey: "limitedTool",
      workflow: "destinationResearch",
    });

    await guarded({ query: "test" });

    expect(mockRunWithGuardrails).toHaveBeenCalledWith(
      expect.objectContaining({
        rateLimit,
      }),
      { query: "test" },
      execute
    );
  });

  it("returns result from guardrails", async () => {
    const schema = z.object({ value: z.number() });
    const execute = vi.fn();
    mockRunWithGuardrails.mockResolvedValue({
      cacheHit: true,
      result: "cached-result",
    });

    const guarded = buildGuardedTool({
      execute,
      schema,
      toolKey: "testTool",
      workflow: "router",
    });

    const result = await guarded({ value: 42 });

    expect(result).toBe("cached-result");
    expect(execute).not.toHaveBeenCalled(); // Cache hit, so execute not called
  });

  it("propagates errors from guardrails", async () => {
    const schema = z.object({ input: z.string() });
    const execute = vi.fn();
    const error = new Error("Rate limit exceeded");
    mockRunWithGuardrails.mockRejectedValue(error);

    const guarded = buildGuardedTool({
      execute,
      schema,
      toolKey: "testTool",
      workflow: "flightSearch",
    });

    await expect(guarded({ input: "test" })).rejects.toThrow("Rate limit exceeded");
  });

  it("works with all optional configurations", async () => {
    const schema = z.object({ data: z.string() });
    const execute = vi.fn().mockResolvedValue("done");
    const cache = {
      hashInput: false,
      key: "simple:cache",
      ttlSeconds: 60,
    };
    const rateLimit = {
      identifier: "ip-192.168.1.1",
      limit: 5,
      window: "1 m",
    };

    const guarded = buildGuardedTool({
      cache,
      execute,
      rateLimit,
      schema,
      toolKey: "fullTool",
      workflow: "itineraryPlanning",
    });

    await guarded({ data: "test" });

    expect(mockRunWithGuardrails).toHaveBeenCalledWith(
      {
        cache,
        parametersSchema: schema,
        rateLimit,
        tool: "fullTool",
        workflow: "itineraryPlanning",
      },
      { data: "test" },
      execute
    );
  });
});
