/** @vitest-environment node */

import { getTravelAdvisory } from "@ai/tools/server/travel-advisory";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { buildUpstashCacheMock } from "@/test/mocks/cache";

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

vi.mock("@/lib/cache/upstash", async () => {
  const { buildUpstashCacheMock: factory } = await import("@/test/mocks/cache");
  const cache = factory();
  (globalThis as Record<string, unknown>).__upstashCache = cache;
  return cache.module;
});

function getUpstashCache(): ReturnType<typeof buildUpstashCacheMock> {
  return (globalThis as Record<string, unknown>).__upstashCache as ReturnType<
    typeof buildUpstashCacheMock
  >;
}

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn((_name: string, _options, fn) => fn()),
}));

describe("getTravelAdvisory", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getUpstashCache().reset();
  });

  it("returns stub for unmappable destinations", async () => {
    if (!getTravelAdvisory.execute) {
      throw new Error("getTravelAdvisory.execute is undefined");
    }
    const result = await getTravelAdvisory.execute(
      {
        destination: "Tokyo",
      },
      mockContext
    );
    expect(result).toMatchObject({
      categories: [],
      overallScore: 75,
      provider: "stub",
    });
  });

  it("validates input schema", async () => {
    if (!getTravelAdvisory.execute) {
      throw new Error("getTravelAdvisory.execute is undefined");
    }
    await expect(
      getTravelAdvisory.execute(
        {
          destination: "",
        },
        mockContext
      )
    ).rejects.toThrow();
  });
});
