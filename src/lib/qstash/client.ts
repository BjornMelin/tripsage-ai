/**
 * @fileoverview QStash client factory with test injection support.
 *
 * Provides centralized QStash client creation with a factory pattern
 * that allows tests to inject mock implementations.
 */

import "server-only";

import { Client } from "@upstash/qstash";
import { getServerEnvVar } from "@/lib/env/server";

/**
 * QStash client interface for dependency injection.
 * Matches the subset of Client methods we use.
 */
// biome-ignore lint/style/useNamingConvention: mirrors @upstash/qstash API naming
export type QStashClientLike = {
  // biome-ignore lint/style/useNamingConvention: mirrors @upstash/qstash method name
  publishJSON: (opts: {
    url: string;
    body: unknown;
    headers?: Record<string, string>;
    retries?: number;
    delay?: number;
    deduplicationId?: string;
    callback?: string;
  }) => Promise<{ messageId: string; url?: string; scheduled?: boolean }>;
};

// Test injection point (follows factory.ts pattern)
let testClientFactory: (() => QStashClientLike) | null = null;

/**
 * Override QStash client factory for tests.
 * Pass null to reset to production behavior.
 *
 * @example
 * ```ts
 * import { setQStashClientFactoryForTests } from "@/lib/qstash/client";
 * import { createQStashMock } from "@/test/upstash/qstash-mock";
 *
 * const qstash = createQStashMock();
 * setQStashClientFactoryForTests(() => new qstash.Client({ token: "test" }));
 *
 * // After tests
 * setQStashClientFactoryForTests(null);
 * ```
 */
// biome-ignore lint/style/useNamingConvention: mirrors QStash naming
export function setQStashClientFactoryForTests(
  factory: (() => QStashClientLike) | null
): void {
  testClientFactory = factory;
}

/**
 * Get QStash client instance.
 * Uses test factory if set, otherwise creates production client.
 */
// biome-ignore lint/style/useNamingConvention: mirrors QStash naming
export function getQStashClient(): QStashClientLike {
  if (testClientFactory) return testClientFactory();
  const token = getServerEnvVar("QSTASH_TOKEN");
  return new Client({ token });
}
