/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

const START_ACTIVE_SPAN = vi.hoisted(() => vi.fn());
const EMIT_ALERT = vi.hoisted(() => vi.fn());

vi.mock("@/lib/telemetry/tracer", () => ({
  getTelemetryTracer: () => ({
    startActiveSpan: (...args: Parameters<typeof START_ACTIVE_SPAN>) =>
      START_ACTIVE_SPAN(...args),
  }),
  TELEMETRY_SERVICE_NAME: "tripsage-frontend",
}));

vi.mock("@/lib/telemetry/alerts", () => ({
  emitOperationalAlert: (...args: Parameters<typeof EMIT_ALERT>) => EMIT_ALERT(...args),
}));

// Reset modules to ensure fresh imports with mocks applied
vi.resetModules();

const { resetRedisWarningStateForTests, warnRedisUnavailable } = await import(
  "@/lib/telemetry/redis"
);

describe("warnRedisUnavailable", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetRedisWarningStateForTests();
    START_ACTIVE_SPAN.mockImplementation((...args: unknown[]) => {
      const callback = args.at(-1) as (span: {
        addEvent: (name: string, attrs: Record<string, string>) => void;
        end: () => void;
        recordException: (error: Error) => void;
        setStatus: (status: Record<string, unknown>) => void;
      }) => unknown;
      return callback({
        addEvent: vi.fn(),
        end: vi.fn(),
        recordException: vi.fn(),
        setStatus: vi.fn(),
      });
    });
  });

  it("records telemetry span and emits alert only once per feature", () => {
    warnRedisUnavailable("cache.tags");
    warnRedisUnavailable("cache.tags");

    expect(START_ACTIVE_SPAN).toHaveBeenCalledTimes(1);
    expect(START_ACTIVE_SPAN).toHaveBeenCalledWith(
      "redis.unavailable",
      { attributes: { "error.name": "RedisUnavailable", feature: "cache.tags" } },
      expect.any(Function)
    );
    expect(EMIT_ALERT).toHaveBeenCalledTimes(1);
    expect(EMIT_ALERT).toHaveBeenCalledWith("redis.unavailable", {
      attributes: {
        errorMessage: "Redis client not configured",
        errorName: "RedisUnavailable",
        feature: "cache.tags",
      },
    });
  });

  it("emits alert for each unique feature", () => {
    warnRedisUnavailable("cache.tags");
    warnRedisUnavailable("cache.lock");

    expect(EMIT_ALERT).toHaveBeenCalledTimes(2);
    expect(EMIT_ALERT.mock.calls.map((call) => call[1])).toEqual([
      {
        attributes: {
          errorMessage: "Redis client not configured",
          errorName: "RedisUnavailable",
          feature: "cache.tags",
        },
      },
      {
        attributes: {
          errorMessage: "Redis client not configured",
          errorName: "RedisUnavailable",
          feature: "cache.lock",
        },
      },
    ]);
  });

  it("includes custom error details when provided", () => {
    warnRedisUnavailable("cache.custom", {
      errorMessage: "Connection refused",
      errorName: "ConnectionError",
    });

    expect(EMIT_ALERT).toHaveBeenCalledWith("redis.unavailable", {
      attributes: {
        errorMessage: "Connection refused",
        errorName: "ConnectionError",
        feature: "cache.custom",
      },
    });
  });
});
