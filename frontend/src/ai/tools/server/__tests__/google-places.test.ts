/** @vitest-environment node */

import { lookupPoiContext } from "@ai/tools/server/google-places";
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getGoogleMapsServerKey } from "@/lib/env/server";
import { cacheLatLng, getCachedLatLng } from "@/lib/google/caching";
import { server } from "@/test/msw/server";

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
  type WithSpan = typeof actual.withTelemetrySpan;
  type SpanArg = Parameters<WithSpan>[2] extends (span: infer S) => unknown ? S : never;
  return {
    ...actual,
    withTelemetrySpan: vi.fn(
      (
        _name: Parameters<WithSpan>[0],
        _options: Parameters<WithSpan>[1],
        fn: Parameters<WithSpan>[2]
      ) =>
        fn({
          addEvent: vi.fn(),
          recordException: vi.fn(),
          setAttribute: vi.fn(),
        } as unknown as SpanArg)
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

  it("returns stub when API key not configured", async () => {
    vi.mocked(getGoogleMapsServerKey).mockImplementation(() => {
      throw new Error("API key required");
    });

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
    server.use(
      http.post("https://places.googleapis.com/v1/places:searchNearby", () =>
        HttpResponse.json({
          places: [
            {
              displayName: { text: "Test POI" },
              id: "ChIJtest123",
              location: { latitude: 35.6895, longitude: 139.6917 },
              types: ["tourist_attraction"],
            },
          ],
        })
      )
    );

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
