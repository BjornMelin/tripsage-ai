/**
 * @fileoverview Mock implementation of Upstash Ratelimit for testing.
 *
 * Provides a shared in-memory store for Ratelimit operations, simulating
 * Ratelimit behavior with sliding window support and forced outcomes.
 */

type SlidingWindowConfig = {
  limit: number;
  intervalMs: number;
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

export class RatelimitMock {
  static slidingWindow(limit: number, window: string): SlidingWindowConfig {
    return { intervalMs: parseWindow(window), limit };
  }

  private readonly state = new Map<string, CounterState>();
  private forced?: {
    success: boolean;
    remaining?: number;
    limit?: number;
    reset?: number;
  };

  constructor(
    private readonly config: { limiter: SlidingWindowConfig; prefix?: string }
  ) {}

  force(
    result: Partial<{
      success: boolean;
      remaining: number;
      limit: number;
      reset: number;
    }>
  ): void {
    this.forced = {
      limit: result.limit ?? this.config.limiter.limit,
      remaining: result.remaining ?? 0,
      reset: result.reset ?? Date.now() + this.config.limiter.intervalMs,
      success: result.success ?? false,
    };
  }

  resetAll(): void {
    this.state.clear();
    this.forced = undefined;
  }

  limit(identifier: string): Promise<{
    success: boolean;
    limit: number;
    remaining: number;
    reset: number;
  }> {
    if (this.forced) {
      return Promise.resolve({
        limit: this.forced.limit ?? this.config.limiter.limit,
        remaining: this.forced.remaining ?? 0,
        reset: this.forced.reset ?? Date.now() + this.config.limiter.intervalMs,
        success: this.forced.success,
      });
    }

    const now = Date.now();
    const key = `${this.config.prefix ?? "ratelimit"}:${identifier}`;
    const current = this.state.get(key);
    if (!current || current.resetAt <= now) {
      const next: CounterState = {
        remaining: this.config.limiter.limit - 1,
        resetAt: now + this.config.limiter.intervalMs,
      };
      this.state.set(key, next);
      return Promise.resolve({
        limit: this.config.limiter.limit,
        remaining: next.remaining,
        reset: next.resetAt,
        success: true,
      });
    }

    if (current.remaining <= 0) {
      return Promise.resolve({
        limit: this.config.limiter.limit,
        remaining: 0,
        reset: current.resetAt,
        success: false,
      });
    }

    current.remaining -= 1;
    this.state.set(key, current);
    return Promise.resolve({
      limit: this.config.limiter.limit,
      remaining: current.remaining,
      reset: current.resetAt,
      success: true,
    });
  }
}

export type RatelimitMockModule = {
  // biome-ignore lint/style/useNamingConvention: mirrors @upstash/ratelimit export
  Ratelimit: typeof RatelimitMock & {
    slidingWindow: typeof RatelimitMock.slidingWindow;
  };
  __reset: () => void;
};

export function createRatelimitMock(): RatelimitMockModule {
  const slidingWindow = RatelimitMock.slidingWindow;
  const instance = new RatelimitMock({ limiter: slidingWindow(10, "1 m") });
  const reset = () => instance.resetAll();
  const RatelimitCtor = class extends RatelimitMock {
    static slidingWindow = slidingWindow;
    constructor(options: { limiter: SlidingWindowConfig; prefix?: string }) {
      super(options);
      instance.resetAll();
      Object.assign(instance, options);
    }
  };

  return {
    __reset: reset,
    // biome-ignore lint/style/useNamingConvention: mirrors @upstash/ratelimit export
    Ratelimit: RatelimitCtor as unknown as typeof RatelimitMock & {
      slidingWindow: typeof RatelimitMock.slidingWindow;
    },
  };
}
