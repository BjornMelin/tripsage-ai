/**
 * @fileoverview Vitest setup helpers for Upstash mocks.
 *
 * Provides vi.doMock registration that works with --pool=threads.
 * Use these helpers instead of vi.mock() for thread-safe testing.
 */

import { vi } from "vitest";
import {
  installUpstashMocks,
  resetUpstashMocks,
  teardownUpstashMocks,
  type UpstashMocksState,
} from "./index";

/**
 * Register Upstash mocks with Vitest using vi.doMock.
 * Call at module scope before tests.
 *
 * @example
 * ```ts
 * import { registerUpstashMocksWithVitest } from "@/test/upstash/setup";
 *
 * const mocks = registerUpstashMocksWithVitest();
 *
 * beforeEach(() => {
 *   mocks.redis.__reset();
 *   mocks.ratelimit.__reset();
 *   mocks.qstash.__reset();
 * });
 * ```
 */
export function registerUpstashMocksWithVitest(): UpstashMocksState {
  const mocks = installUpstashMocks();

  // Use vi.doMock for thread-safety (not vi.mock which hoists)
  vi.doMock("@upstash/redis", () => ({
    // biome-ignore lint/style/useNamingConvention: matches @upstash/redis export
    Redis: mocks.redis.Redis,
  }));

  vi.doMock("@upstash/ratelimit", () => ({
    // biome-ignore lint/style/useNamingConvention: matches @upstash/ratelimit export
    Ratelimit: mocks.ratelimit.Ratelimit,
  }));

  vi.doMock("@upstash/qstash", () => ({
    // biome-ignore lint/style/useNamingConvention: matches @upstash/qstash export
    Client: mocks.qstash.Client,
    // biome-ignore lint/style/useNamingConvention: matches @upstash/qstash export
    Receiver: mocks.qstash.Receiver,
  }));

  return mocks;
}

/**
 * Create lifecycle hooks for Upstash test isolation (direct/mock-first tests).
 *
 * Returns mock state without registering vi.doMock. Use this when:
 * - Testing directly against mock instances (mock-first approach)
 * - Manually injecting mocks via factory setters or dependency injection
 * - You don't need module-level import replacement
 *
 * For tests that require module-level mock replacement (importing the real module
 * and having it transparently use mocks), use setupUpstashTestEnvironment() instead.
 *
 * @example
 * ```ts
 * import { createUpstashTestHooks } from "@/test/upstash/setup";
 * import { beforeEach, afterAll } from "vitest";
 *
 * const { beforeEachHook, afterAllHook, mocks } = createUpstashTestHooks();
 * beforeEach(beforeEachHook);
 * afterAll(afterAllHook);
 *
 * // Use mocks directly or inject via factories:
 * setQStashClientFactoryForTests(() => mocks.qstash.Client);
 * // ... tests that call getQStashClient() will use the mock
 * ```
 */
export function createUpstashTestHooks(): {
  beforeEachHook: () => void;
  afterAllHook: () => void;
  mocks: UpstashMocksState;
} {
  const mocks = installUpstashMocks();
  return {
    afterAllHook: () => teardownUpstashMocks(),
    beforeEachHook: () => resetUpstashMocks(),
    mocks,
  };
}

/**
 * Full setup helper that registers mocks AND returns lifecycle hooks.
 * Combines registerUpstashMocksWithVitest() and createUpstashTestHooks().
 *
 * @example
 * ```ts
 * import { setupUpstashTestEnvironment } from "@/test/upstash/setup";
 * import { beforeEach, afterAll } from "vitest";
 *
 * const { beforeEachHook, afterAllHook, mocks } = setupUpstashTestEnvironment();
 * beforeEach(beforeEachHook);
 * afterAll(afterAllHook);
 * ```
 */
export function setupUpstashTestEnvironment(): {
  beforeEachHook: () => void;
  afterAllHook: () => void;
  mocks: UpstashMocksState;
} {
  const mocks = registerUpstashMocksWithVitest();
  return {
    afterAllHook: () => teardownUpstashMocks(),
    beforeEachHook: () => resetUpstashMocks(),
    mocks,
  };
}
