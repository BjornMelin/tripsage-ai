import { beforeEach, describe, expect, it, vi } from "vitest";
import { getGoogleMapsServerKey } from "@/lib/env/server";
import { cacheLatLng, getCachedLatLng } from "@/lib/google/caching";

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

vi.mock("@/lib/google/caching", () => ({
  cacheLatLng: vi.fn().mockResolvedValue(undefined),
  getCachedLatLng: vi.fn().mockResolvedValue(null),
}));

vi.mock("@/lib/env/server", () => ({
  getGoogleMapsServerKey: vi.fn().mockReturnValue("test-server-key"),
  getServerEnvVar: vi.fn(() => undefined),
  getServerEnvVarWithFallback: vi.fn((_key: string, fallback?: string) => fallback),
}));

vi.mock("@/lib/telemetry/span", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/telemetry/span")>(
      "@/lib/telemetry/span"
    );
  return {
    ...actual,
    withTelemetrySpan: vi.fn((_name: string, _options, fn) =>
      fn({
        addEvent: vi.fn(),
        recordException: vi.fn(),
        setAttribute: vi.fn(),
      })
    ),
  };
});

describe("lookupPoiContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getCachedLatLng).mockResolvedValue(null);
    vi.mocked(cacheLatLng).mockResolvedValue(undefined);
    vi.mocked(getGoogleMapsServerKey).mockReturnValue("test-server-key");
  });

  const loadTool = async () =>
    (await import("@/ai/tools/server/google-places")).lookupPoiContext;

  it("returns stub when API key not configured", async () => {
    vi.mocked(getGoogleMapsServerKey).mockImplementation(() => {
      throw new Error("API key required");
    });

    const lookupPoiContext = await loadTool();
    const exec = lookupPoiContext.execute as
      | ((params: unknown, ctx: unknown) => Promise<unknown>)
      | undefined;
    if (!exec) {
      throw new Error("lookupPoiContext.execute is undefined");
    }
    const result = await exec(
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
    const lookupPoiContext = await loadTool();
    const exec = lookupPoiContext.execute as
      | ((params: unknown, ctx: unknown) => Promise<unknown>)
      | undefined;
    if (!exec) {
      throw new Error("lookupPoiContext.execute is undefined");
    }
    await expect(
      exec(
        {
          // Missing destination, query, and lat/lon
          radiusMeters: 1000,
        },
        mockContext
      )
    ).rejects.toThrow();
  });

  it("handles coordinates input", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      json: async () => ({
        places: [
          {
            displayName: { text: "Test POI" },
            id: "ChIJtest123",
            location: { latitude: 35.6895, longitude: 139.6917 },
            types: ["tourist_attraction"],
          },
        ],
      }),
      ok: true,
    });

    const lookupPoiContext = await loadTool();
    const exec = lookupPoiContext.execute as
      | ((params: unknown, ctx: unknown) => Promise<unknown>)
      | undefined;
    if (!exec) {
      throw new Error("lookupPoiContext.execute is undefined");
    }
    const result = (await exec(
      {
        lat: 35.6895,
        lon: 139.6917,
        radiusMeters: 1000,
      },
      mockContext
    )) as unknown;

    expect(result).toMatchObject({
      pois: expect.arrayContaining([
        expect.objectContaining({
          lat: 35.6895,
          lon: 139.6917,
          name: "Test POI",
          placeId: "ChIJtest123",
        }),
      ]),
      provider: "googleplaces",
    });
  });
});
