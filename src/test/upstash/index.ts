/**
 * @fileoverview Unified Upstash testing harness public API.
 *
 * Provides a single entry point for all Upstash mock modules (Redis, Ratelimit, QStash)
 * with lifecycle helpers for test setup, reset, and teardown.
 *
 * @example
 * ```ts
 * import {
 *   installUpstashMocks,
 *   resetUpstashMocks,
 *   getPublishedQStashMessages,
 * } from "@/test/upstash";
 *
 * const mocks = installUpstashMocks();
 *
 * beforeEach(() => resetUpstashMocks());
 *
 * it("tracks QStash messages", async () => {
 *   // ... code that calls publishJSON
 *   expect(getPublishedQStashMessages()).toHaveLength(1);
 * });
 * ```
 */

// Imports for unified API
import {
  createQStashMock,
  type QStashMessage,
  type QStashMockModule,
} from "./qstash-mock";
import { createRatelimitMock, type RatelimitMockModule } from "./ratelimit-mock";
import {
  createRedisMock,
  type RedisMockModule,
  sharedUpstashStore,
} from "./redis-mock";

// Re-export test constants
export {
  TEST_QSTASH_NEXT_SIGNING_KEY,
  TEST_QSTASH_SIGNING_KEY,
  TEST_QSTASH_TOKEN,
  TEST_REDIS_TOKEN,
  TEST_REDIS_URL,
} from "./constants";

export type {
  QStashMessage,
  QStashMockModule,
  QStashPublishOptions,
  QStashPublishResult,
} from "./qstash-mock";
// Re-export QStash mock
export {
  createQStashMock,
  forceVerifyOutcome,
  getPublishedMessages,
  QStashClientMock,
  QStashReceiverMock,
  resetQStashMock,
} from "./qstash-mock";
export type { RatelimitMockModule } from "./ratelimit-mock";
// Re-export Ratelimit mock
export { createRatelimitMock, RatelimitMock } from "./ratelimit-mock";
export type {
  RedisMockModule,
  UpstashMemoryStore,
  UpstashMocks,
} from "./redis-mock";
// Re-export Redis mock
export {
  createRedisMock,
  createUpstashMemoryStore,
  RedisMock,
  RedisMockClient,
  resetRedisStore,
  runUpstashCommand,
  runUpstashPipeline,
  setupUpstashMocks,
  sharedUpstashStore,
} from "./redis-mock";

/**
 * Unified state type for all Upstash mocks.
 */
export type UpstashMocksState = {
  redis: RedisMockModule;
  ratelimit: RatelimitMockModule;
  qstash: QStashMockModule;
  installed: boolean;
};

let state: UpstashMocksState | null = null;

/**
 * Install all Upstash mocks. Call once at test suite setup.
 * Returns mock modules for vi.doMock() registration.
 *
 * @example
 * ```ts
 * const mocks = installUpstashMocks();
 *
 * vi.doMock("@upstash/redis", () => ({ Redis: mocks.redis.Redis }));
 * vi.doMock("@upstash/ratelimit", () => ({ Ratelimit: mocks.ratelimit.Ratelimit }));
 * vi.doMock("@upstash/qstash", () => ({
 *   Client: mocks.qstash.Client,
 *   Receiver: mocks.qstash.Receiver,
 * }));
 * ```
 */
export function installUpstashMocks(): UpstashMocksState {
  if (state) return state;
  state = {
    installed: true,
    qstash: createQStashMock(),
    ratelimit: createRatelimitMock(),
    redis: createRedisMock(sharedUpstashStore),
  };
  return state;
}

/**
 * Reset all mock state between tests. Call in beforeEach().
 */
export function resetUpstashMocks(): void {
  if (!state) return;
  state.redis.__reset();
  state.ratelimit.__reset();
  state.qstash.__reset();
}

/**
 * Teardown mocks after test suite. Call in afterAll().
 */
export function teardownUpstashMocks(): void {
  resetUpstashMocks();
  state = null;
}

/**
 * Get published QStash messages for assertions.
 */
// biome-ignore lint/style/useNamingConvention: mirrors QStash naming
export function getPublishedQStashMessages(): QStashMessage[] {
  if (!state) return [];
  return state.qstash.__getMessages();
}

/**
 * Force QStash signature verification outcome.
 * @param outcome - true/false for verify result, or Error to throw
 */
// biome-ignore lint/style/useNamingConvention: mirrors QStash naming
export function forceQStashVerifyOutcome(outcome: boolean | Error): void {
  if (!state) throw new Error("Call installUpstashMocks() first");
  state.qstash.__forceVerify(outcome);
}

/**
 * Get current mock state (for advanced use cases).
 * Returns null if installUpstashMocks() has not been called.
 */
export function getUpstashMocksState(): UpstashMocksState | null {
  return state;
}
