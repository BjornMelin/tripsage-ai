/**
 * @fileoverview Mock implementation of Upstash Ratelimit for testing.
 *
 * Provides a shared in-memory store for Ratelimit operations, simulating
 * Ratelimit behavior with sliding/fixed window support and forced outcomes.
 * Compatible with vi.doMock() for thread-safe testing with --pool=threads.
 */

type LimiterConfig = {
  limit: number;
  intervalMs: number;
  type: "sliding" | "fixed";
};

type CounterState = {
  remaining: number;
  resetAt: number;
  windowStart?: number;
};

type ForcedOverrides = Partial<{
  success: boolean;
  remaining: number;
  limit: number;
  reset: number;
  retryAfter: number;
}>;

function parseWindow(window: string): number {
  const [valueRaw, unit] = window.trim().split(/\s+/);
  const value = Number(valueRaw);
  if (Number.isNaN(value)) return 60000;
  switch (unit) {
    case "s":
    case "sec":
    case "seconds":
      return value * 1000;
    case "m":
    case "min":
    case "minute":
    case "minutes":
      return value * 60_000;
    case "h":
    case "hr":
    case "hour":
    case "hours":
      return value * 3_600_000;
    default:
      return value * 1000;
  }
}

export type RatelimitMockModule = {
  // biome-ignore lint/style/useNamingConvention: mirrors @upstash/ratelimit export shape
  Ratelimit: RatelimitMockClass & {
    slidingWindow: (limit: number, window: string) => LimiterConfig;
    fixedWindow: (limit: number, window: string) => LimiterConfig;
  };
  __getRecordedIdentifiers: () => string[];
  __getLimitCallCount: () => number;
  __reset: () => void;
  __force: (
    result: Partial<{
      success: boolean;
      remaining: number;
      limit: number;
      reset: number;
      retryAfter: number;
    }>
  ) => void;
};

type RatelimitMockClass = new (config: {
  limiter: LimiterConfig;
  prefix?: string;
}) => RatelimitMockInstance;

type RatelimitMockInstance = {
  limit: (identifier: string) => Promise<{
    success: boolean;
    limit: number;
    remaining: number;
    reset: number;
    retryAfter: number;
  }>;
  force: (
    result: Partial<{
      success: boolean;
      remaining: number;
      limit: number;
      reset: number;
      retryAfter: number;
    }>
  ) => void;
};

/**
 * Create Ratelimit mock module for vi.doMock() registration.
 * Each call creates an isolated mock with its own shared state.
 *
 * @example
 * ```ts
 * const ratelimit = createRatelimitMock();
 *
 * vi.doMock("@upstash/ratelimit", () => ({
 *   Ratelimit: ratelimit.Ratelimit,
 * }));
 *
 * beforeEach(() => ratelimit.__reset());
 * ```
 */
export function createRatelimitMock(): RatelimitMockModule {
  // Shared state for all limiter instances created by this mock
  const globalState = new Map<string, CounterState>();
  const perInstanceForced = new Map<string, ForcedOverrides>();
  const recordedIdentifiers: string[] = [];
  let globalForced: ForcedOverrides | undefined;
  let limitCallCount = 0;
  let instanceSeq = 0;

  const resolveForcedOutcome = (
    forced: ForcedOverrides | undefined,
    limiter: LimiterConfig
  ) => {
    if (!forced) return undefined;
    return {
      limit: forced.limit ?? limiter.limit,
      remaining: forced.remaining ?? 0,
      reset: forced.reset ?? Date.now() + limiter.intervalMs,
      retryAfter: forced.retryAfter ?? 1,
      success: forced.success ?? false,
    };
  };

  /**
   * Ratelimit limiter instance with proper state isolation.
   */
  class RatelimitInstance {
    private readonly config: { limiter: LimiterConfig; prefix?: string };
    private readonly instanceId: string;

    constructor(config: { limiter: LimiterConfig; prefix?: string }) {
      this.config = config;
      this.instanceId = `rl-${++instanceSeq}`;
    }

    force(
      result: Partial<{
        success: boolean;
        remaining: number;
        limit: number;
        reset: number;
        retryAfter: number;
      }>
    ): void {
      perInstanceForced.set(this.instanceId, {
        limit: result.limit ?? this.config.limiter.limit,
        remaining: result.remaining ?? 0,
        reset: result.reset ?? Date.now() + this.config.limiter.intervalMs,
        retryAfter: result.retryAfter ?? 1,
        success: result.success ?? false,
      });
    }

    limit(identifier: string): Promise<{
      success: boolean;
      limit: number;
      remaining: number;
      reset: number;
      retryAfter: number;
    }> {
      recordedIdentifiers.push(identifier);
      limitCallCount += 1;

      const forced = resolveForcedOutcome(
        perInstanceForced.get(this.instanceId) ?? globalForced,
        this.config.limiter
      );
      if (forced) {
        return Promise.resolve(forced);
      }

      // Check for forced outcome first
      const now = Date.now();
      const key = `${this.config.prefix ?? "ratelimit"}:${identifier}`;
      const current = globalState.get(key);
      const { limit, intervalMs, type } = this.config.limiter;

      // Fixed window: count resets on aligned window boundaries
      if (type === "fixed") {
        const windowStart = Math.floor(now / intervalMs) * intervalMs;
        const windowEnd = windowStart + intervalMs;
        if (!current || current.windowStart !== windowStart) {
          const next: CounterState = {
            remaining: limit - 1,
            resetAt: windowEnd,
            windowStart,
          };
          globalState.set(key, next);
          return Promise.resolve({
            limit,
            remaining: next.remaining,
            reset: windowEnd,
            retryAfter: 0,
            success: true,
          });
        }

        if (current.remaining <= 0) {
          return Promise.resolve({
            limit,
            remaining: 0,
            reset: current.resetAt,
            retryAfter: Math.max(1, Math.ceil((current.resetAt - now) / 1000)),
            success: false,
          });
        }

        current.remaining -= 1;
        globalState.set(key, current);
        return Promise.resolve({
          limit,
          remaining: current.remaining,
          reset: current.resetAt,
          retryAfter: 0,
          success: true,
        });
      }

      // Sliding window: reset relative to first request after expiry
      if (!current || current.resetAt <= now) {
        const next: CounterState = {
          remaining: limit - 1,
          resetAt: now + intervalMs,
        };
        globalState.set(key, next);
        return Promise.resolve({
          limit,
          remaining: next.remaining,
          reset: next.resetAt,
          retryAfter: 0,
          success: true,
        });
      }

      if (current.remaining <= 0) {
        return Promise.resolve({
          limit,
          remaining: 0,
          reset: current.resetAt,
          retryAfter: Math.max(1, Math.ceil((current.resetAt - now) / 1000)),
          success: false,
        });
      }

      current.remaining -= 1;
      globalState.set(key, current);
      return Promise.resolve({
        limit,
        remaining: current.remaining,
        reset: current.resetAt,
        retryAfter: 0,
        success: true,
      });
    }
  }

  // Add static methods to the constructor while keeping typing explicit
  const RatelimitConstructor = Object.assign(RatelimitInstance, {
    fixedWindow: (limit: number, window: string): LimiterConfig => ({
      intervalMs: parseWindow(window),
      limit,
      type: "fixed",
    }),
    slidingWindow: (limit: number, window: string): LimiterConfig => ({
      intervalMs: parseWindow(window),
      limit,
      type: "sliding",
    }),
  }) as RatelimitMockClass & {
    slidingWindow: (limit: number, window: string) => LimiterConfig;
    fixedWindow: (limit: number, window: string) => LimiterConfig;
  };

  return {
    __force: (result) => {
      globalForced = {
        limit: result.limit,
        remaining: result.remaining ?? 0,
        reset: result.reset ?? Date.now() + 60000,
        retryAfter: result.retryAfter ?? 1,
        success: result.success ?? false,
      };
    },
    __getLimitCallCount: () => limitCallCount,
    __getRecordedIdentifiers: () => [...recordedIdentifiers],
    __reset: () => {
      globalState.clear();
      perInstanceForced.clear();
      instanceSeq = 0;
      globalForced = undefined;
      recordedIdentifiers.length = 0;
      limitCallCount = 0;
    },
    // biome-ignore lint/style/useNamingConvention: mirrors @upstash/ratelimit export shape
    Ratelimit: RatelimitConstructor,
  };
}

// Legacy export for backwards compatibility
// biome-ignore lint/complexity/noStaticOnlyClass: maintains backwards-compatible class API
export class RatelimitMock {
  static slidingWindow(limit: number, window: string): LimiterConfig {
    return { intervalMs: parseWindow(window), limit, type: "sliding" };
  }

  static fixedWindow(limit: number, window: string): LimiterConfig {
    return { intervalMs: parseWindow(window), limit, type: "fixed" };
  }
}
