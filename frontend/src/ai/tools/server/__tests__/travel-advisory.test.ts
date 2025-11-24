/** @vitest-environment node */

import { getTravelAdvisory } from "@ai/tools/server/travel-advisory";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { buildUpstashCacheMock } from "@/test/mocks";

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

let upstashCache: ReturnType<typeof buildUpstashCacheMock>;
const cacheFactory = vi.hoisted(() => {
  return () => {
    if (!upstashCache) {
      upstashCache = buildUpstashCacheMock();
    }
    return upstashCache.module;
  };
});

vi.mock("@/lib/cache/upstash", () => cacheFactory());

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn((_name: string, _options, fn) => fn()),
}));

describe("getTravelAdvisory", () => {
  beforeEach(() => {
    // Initialize cache if not already done
    if (!upstashCache) {
      upstashCache = buildUpstashCacheMock();
    }
    vi.clearAllMocks();
    upstashCache.reset();
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
