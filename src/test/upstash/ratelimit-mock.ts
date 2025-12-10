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
};

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
  let globalForced:
    | {
        success: boolean;
        remaining?: number;
        limit?: number;
        reset?: number;
        retryAfter?: number;
      }
    | undefined;

  /**
   * Ratelimit limiter instance with proper state isolation.
   */
  class RatelimitInstance {
    private readonly config: { limiter: LimiterConfig; prefix?: string };

    constructor(config: { limiter: LimiterConfig; prefix?: string }) {
      this.config = config;
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
      globalForced = {
        limit: result.limit ?? this.config.limiter.limit,
        remaining: result.remaining ?? 0,
        reset: result.reset ?? Date.now() + this.config.limiter.intervalMs,
        retryAfter: result.retryAfter ?? 1,
        success: result.success ?? false,
      };
    }

    limit(identifier: string): Promise<{
      success: boolean;
      limit: number;
      remaining: number;
      reset: number;
      retryAfter: number;
    }> {
      // Check for forced outcome first
      if (globalForced) {
        return Promise.resolve({
          limit: globalForced.limit ?? this.config.limiter.limit,
          remaining: globalForced.remaining ?? 0,
          reset: globalForced.reset ?? Date.now() + this.config.limiter.intervalMs,
          retryAfter: globalForced.retryAfter ?? 1,
          success: globalForced.success,
        });
      }

      const now = Date.now();
      const key = `${this.config.prefix ?? "ratelimit"}:${identifier}`;
      const current = globalState.get(key);

      // New window or expired window
      if (!current || current.resetAt <= now) {
        const next: CounterState = {
          remaining: this.config.limiter.limit - 1,
          resetAt: now + this.config.limiter.intervalMs,
        };
        globalState.set(key, next);
        return Promise.resolve({
          limit: this.config.limiter.limit,
          remaining: next.remaining,
          reset: next.resetAt,
          retryAfter: 0,
          success: true,
        });
      }

      // Rate limit exceeded
      if (current.remaining <= 0) {
        return Promise.resolve({
          limit: this.config.limiter.limit,
          remaining: 0,
          reset: current.resetAt,
          retryAfter: Math.max(1, Math.ceil((current.resetAt - now) / 1000)),
          success: false,
        });
      }

      // Consume one request
      current.remaining -= 1;
      globalState.set(key, current);
      return Promise.resolve({
        limit: this.config.limiter.limit,
        remaining: current.remaining,
        reset: current.resetAt,
        retryAfter: 0,
        success: true,
      });
    }
  }

  // Add static methods to the constructor
  const RatelimitConstructor = RatelimitInstance as unknown as RatelimitMockClass & {
    slidingWindow: (limit: number, window: string) => LimiterConfig;
    fixedWindow: (limit: number, window: string) => LimiterConfig;
  };

  RatelimitConstructor.slidingWindow = (
    limit: number,
    window: string
  ): LimiterConfig => ({
    intervalMs: parseWindow(window),
    limit,
    type: "sliding",
  });

  RatelimitConstructor.fixedWindow = (
    limit: number,
    window: string
  ): LimiterConfig => ({
    intervalMs: parseWindow(window),
    limit,
    type: "fixed",
  });

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
    __reset: () => {
      globalState.clear();
      globalForced = undefined;
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
