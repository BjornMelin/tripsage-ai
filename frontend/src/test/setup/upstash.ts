/**
 * @fileoverview Setup helper for Upstash mocks and MSW handlers.
 */

import { vi } from "vitest";
import { createRatelimitMock, createRedisMock } from "@/test/upstash";

export type UpstashMocks = {
  redis: ReturnType<typeof createRedisMock>;
  ratelimit: ReturnType<typeof createRatelimitMock>;
};

/**
 * Registers shared Upstash mocks (`@upstash/redis`, `@upstash/ratelimit`) and
 * returns helpers to reset between tests. Intended for hoisted use in Vitest.
 */
export function setupUpstashMocks(): UpstashMocks {
  const redis = createRedisMock();
  const ratelimit = createRatelimitMock();

  vi.mock("@upstash/redis", () => redis);
  vi.mock("@upstash/ratelimit", () => ratelimit);

  return { ratelimit, redis };
}
