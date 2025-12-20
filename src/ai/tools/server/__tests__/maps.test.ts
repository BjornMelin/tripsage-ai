/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => undefined),
}));

const mockGetGeocode = vi.fn();
const mockPostComputeRouteMatrix = vi.fn();
const mockParseNdjsonResponse = vi.fn();

vi.mock("@/lib/google/client", () => ({
  getGeocode: (...args: unknown[]) => mockGetGeocode(...args),
  parseNdjsonResponse: (...args: unknown[]) => mockParseNdjsonResponse(...args),
  postComputeRouteMatrix: (...args: unknown[]) => mockPostComputeRouteMatrix(...args),
}));

vi.mock("@/lib/env/server", () => ({
  getGoogleMapsServerKey: () => "test-key",
}));

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn((_name: string, _options, fn) =>
    fn({
      addEvent: vi.fn(),
      setAttribute: vi.fn(),
    })
  ),
}));

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

function isAsyncIterable(value: unknown): value is AsyncIterable<unknown> {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as { [Symbol.asyncIterator]?: unknown })[Symbol.asyncIterator] ===
      "function"
  );
}

async function resolveToolResult<T>(value: T | AsyncIterable<T>): Promise<T> {
  if (isAsyncIterable(value)) {
    let last: T | undefined;
    for await (const chunk of value) {
      last = chunk;
    }
    if (last === undefined) {
      throw new Error("AsyncIterable produced no values");
    }
    return last;
  }
  return value;
}

const geocodeResponse = {
  results: [
    {
      formatted_address: "Test Address",
      geometry: { location: { lat: 37.77, lng: -122.42 } },
      place_id: "place_123",
    },
  ],
  status: "OK",
};

describe("maps tools", () => {
  beforeEach(() => {
    mockGetGeocode.mockResolvedValue({
      json: async () => geocodeResponse,
      ok: true,
    });
    mockPostComputeRouteMatrix.mockResolvedValue({
      ok: true,
      text: async () => "",
    });
    mockParseNdjsonResponse.mockResolvedValue([
      {
        condition: "ROUTE_EXISTS",
        destinationIndex: 0,
        distanceMeters: 1000,
        duration: "120s",
        originIndex: 0,
      },
      {
        condition: "ROUTE_NOT_FOUND",
        destinationIndex: 1,
        originIndex: 0,
      },
    ]);
  });

  it("returns normalized distance matrix entries", async () => {
    const { distanceMatrix } = await import("@ai/tools/server/maps");
    if (!distanceMatrix.execute) {
      throw new Error("distanceMatrix.execute is undefined");
    }

    const result = await resolveToolResult(
      await distanceMatrix.execute(
        {
          destinations: ["Destination A", "Destination B"],
          origins: ["Origin A"],
          units: "metric",
        },
        mockContext
      )
    );

    expect(result).toMatchObject({
      destinations: ["Destination A", "Destination B"],
      origins: ["Origin A"],
      units: "metric",
    });
    expect(result.entries).toHaveLength(2);
    expect(result.entries[0]).toMatchObject({
      destinationIndex: 0,
      distanceMeters: 1000,
      distanceText: "1.0 km",
      durationSeconds: 120,
      durationText: "2 mins",
      originIndex: 0,
      status: "OK",
    });
    expect(result.entries[1]).toMatchObject({
      destinationIndex: 1,
      distanceMeters: null,
      distanceText: null,
      durationSeconds: null,
      durationText: null,
      originIndex: 0,
      status: "ZERO_RESULTS",
    });
  });
});
