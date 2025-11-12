import { beforeEach, describe, expect, it, vi } from "vitest";

import { getTravelAdvisory } from "../travel-advisory";

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

vi.mock("@/lib/cache/upstash", () => ({
  getCachedJson: vi.fn().mockResolvedValue(null),
  setCachedJson: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn((_name, _options, fn) => fn()),
}));

describe("getTravelAdvisory", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Explicitly unset the env var to ensure stub behavior
    process.env.GEOSURE_API_KEY = undefined;
  });

  it("returns stub when API key not configured", async () => {
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

  it("caches results", async () => {
    if (!getTravelAdvisory.execute) {
      throw new Error("getTravelAdvisory.execute is undefined");
    }
    const { getCachedJson } = await import("@/lib/cache/upstash");
    const cached = getCachedJson as ReturnType<typeof vi.fn>;
    cached.mockResolvedValueOnce({
      categories: [],
      destination: "Tokyo",
      overallScore: 80,
      provider: "geosure",
    });

    const result = await getTravelAdvisory.execute(
      {
        destination: "Tokyo",
      },
      mockContext
    );

    expect(result).toMatchObject({
      destination: "Tokyo",
      fromCache: true,
      overallScore: 80,
    });
  });
});
