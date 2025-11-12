import { beforeEach, describe, expect, it, vi } from "vitest";

import { lookupPoiContext } from "../opentripmap";

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

describe("lookupPoiContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Explicitly unset the env var to ensure stub behavior
    process.env.OPENTRIPMAP_API_KEY = undefined;
  });

  it("returns stub when API key not configured", async () => {
    if (!lookupPoiContext.execute) {
      throw new Error("lookupPoiContext.execute is undefined");
    }
    const result = await lookupPoiContext.execute(
      {
        destination: "Tokyo",
        radiusMeters: 1000,
      },
      mockContext
    );
    expect(result).toMatchObject({
      pois: [],
      provider: "stub",
    });
  });

  it("validates input schema", async () => {
    if (!lookupPoiContext.execute) {
      throw new Error("lookupPoiContext.execute is undefined");
    }
    await expect(
      lookupPoiContext.execute(
        {
          // Missing both destination and lat/lon
          radiusMeters: 1000,
        },
        mockContext
      )
    ).rejects.toThrow();
  });

  it("handles coordinates input", async () => {
    process.env.OPENTRIPMAP_API_KEY = "test-key";
    global.fetch = vi.fn().mockResolvedValue({
      json: async () => ({
        features: [
          {
            geometry: {
              coordinates: [139.6917, 35.6895],
              type: "Point",
            },
            properties: {
              kind: "tourism",
              name: "Test POI",
              xid: "test-xid",
            },
            type: "Feature",
          },
        ],
        type: "FeatureCollection",
      }),
      ok: true,
    });

    if (!lookupPoiContext.execute) {
      throw new Error("lookupPoiContext.execute is undefined");
    }
    const result = await lookupPoiContext.execute(
      {
        lat: 35.6895,
        lon: 139.6917,
        radiusMeters: 1000,
      },
      mockContext
    );

    expect(result).toMatchObject({
      pois: expect.arrayContaining([
        expect.objectContaining({
          lat: 35.6895,
          lon: 139.6917,
          name: "Test POI",
        }),
      ]),
      provider: "opentripmap",
    });

    // Ensure radius is passed in meters (no /1000 conversion)
    const calledUrl = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(calledUrl).toMatch(/radius=1000(&|$)/);
  });
});
