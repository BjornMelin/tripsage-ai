/** @vitest-environment node */

import { beforeEach, describe, expect, test, vi } from "vitest";

const mockFetchWithRetry = vi.hoisted(() => vi.fn());
const mockGetServerEnvVar = vi.hoisted(() => vi.fn());

vi.mock("@/lib/http/retry", () => ({
  fetchWithRetry: (...args: unknown[]) => mockFetchWithRetry(...args),
}));

vi.mock("@/lib/env/server", () => ({
  getServerEnvVar: (...args: unknown[]) => mockGetServerEnvVar(...args),
}));

vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => undefined),
}));

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn(
    (_name: string, _opts: unknown, fn: (span: unknown) => unknown) =>
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
    Symbol.asyncIterator in value &&
    typeof (value as { [Symbol.asyncIterator]?: unknown })[Symbol.asyncIterator] ===
      "function"
  );
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    headers: { "content-type": "application/json" },
    status,
  });
}

describe("getCurrentWeather", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetServerEnvVar.mockReturnValue("test-key");
  });

  test("builds correct URL for city query and maps response fields", async () => {
    const { getCurrentWeather } = await import("@ai/tools/server/weather");

    mockFetchWithRetry.mockResolvedValue(
      jsonResponse({
        clouds: { all: 20 },
        main: {
          feels_like: 21.8,
          humidity: 65,
          pressure: 1013,
          temp: 22.5,
          temp_max: 25.0,
          temp_min: 20.0,
        },
        name: "Paris",
        rain: { "1h": 0.5 },
        snow: { "3h": 0.2 },
        sys: { country: "FR", sunrise: 123, sunset: 456 },
        timezone: 3600,
        visibility: 10000,
        weather: [{ description: "clear sky", icon: "01d" }],
        wind: { deg: 180, gust: 5.2, speed: 3.5 },
      })
    );

    const execute = getCurrentWeather.execute;
    if (!execute) throw new Error("getCurrentWeather.execute is undefined");

    const out = await execute(
      {
        city: "Paris",
        coordinates: null,
        fresh: true,
        lang: "en",
        units: "metric",
        zip: null,
      },
      mockContext
    );

    const url = String(mockFetchWithRetry.mock.calls[0]?.[0] ?? "");
    expect(url).toContain("https://api.openweathermap.org/data/2.5/weather");
    expect(url).toContain("q=Paris");
    expect(url).toContain("units=metric");
    expect(url).toContain("lang=en");
    expect(url).toContain("appid=test-key");

    expect(out).toMatchObject({
      city: "Paris",
      clouds: 20,
      country: "FR",
      description: "clear sky",
      feelsLike: 21.8,
      fromCache: false,
      humidity: 65,
      icon: "01d",
      pressure: 1013,
      provider: "http_get",
      rain: 0.5,
      snow: 0.2,
      status: "success",
      sunrise: 123,
      sunset: 456,
      temp: 22.5,
      tempMax: 25,
      tempMin: 20,
      timezone: 3600,
      visibility: 10000,
      windDirection: 180,
      windGust: 5.2,
      windSpeed: 3.5,
    });
    if (isAsyncIterable(out)) {
      throw new Error("Unexpected streaming tool output in test");
    }
    expect(typeof out.tookMs).toBe("number");
  });

  test("uses coordinates when provided", async () => {
    const { getCurrentWeather } = await import("@ai/tools/server/weather");
    mockFetchWithRetry.mockResolvedValue(
      jsonResponse({ main: { temp: 20 }, name: "X" })
    );

    const execute = getCurrentWeather.execute;
    if (!execute) throw new Error("getCurrentWeather.execute is undefined");

    await execute(
      {
        city: null,
        coordinates: { lat: 48.8566, lon: 2.3522 },
        fresh: true,
        lang: null,
        units: "metric",
        zip: null,
      },
      mockContext
    );

    const url = String(mockFetchWithRetry.mock.calls[0]?.[0] ?? "");
    expect(url).toContain("lat=48.8566");
    expect(url).toContain("lon=2.3522");
  });

  test("uses zip when provided", async () => {
    const { getCurrentWeather } = await import("@ai/tools/server/weather");
    mockFetchWithRetry.mockResolvedValue(
      jsonResponse({ main: { temp: 20 }, name: "X" })
    );

    const execute = getCurrentWeather.execute;
    if (!execute) throw new Error("getCurrentWeather.execute is undefined");

    await execute(
      {
        city: null,
        coordinates: null,
        fresh: true,
        lang: null,
        units: "metric",
        zip: "10001",
      },
      mockContext
    );

    const url = String(mockFetchWithRetry.mock.calls[0]?.[0] ?? "");
    expect(url).toContain("zip=10001");
  });

  test("fails closed when not configured", async () => {
    const { getCurrentWeather } = await import("@ai/tools/server/weather");
    mockGetServerEnvVar.mockImplementation(() => {
      throw new Error("Missing env OPENWEATHERMAP_API_KEY");
    });

    const execute = getCurrentWeather.execute;
    if (!execute) throw new Error("getCurrentWeather.execute is undefined");

    await expect(
      execute(
        {
          city: "Paris",
          coordinates: null,
          fresh: true,
          lang: null,
          units: "metric",
          zip: null,
        },
        mockContext
      )
    ).rejects.toMatchObject({ code: "weather_not_configured" });
  });

  test.each([
    ["fetch_timeout", "weather_timeout"],
    ["fetch_failed", "weather_failed"],
  ])("maps %s to domain error code", async (code, expected) => {
    const { getCurrentWeather } = await import("@ai/tools/server/weather");
    mockFetchWithRetry.mockRejectedValue(Object.assign(new Error("boom"), { code }));

    const execute = getCurrentWeather.execute;
    if (!execute) throw new Error("getCurrentWeather.execute is undefined");

    await expect(
      execute(
        {
          city: "Paris",
          coordinates: null,
          fresh: true,
          lang: null,
          units: "metric",
          zip: null,
        },
        mockContext
      )
    ).rejects.toMatchObject({ code: expected });
  });

  test.each([
    [429, "weather_rate_limited"],
    [401, "weather_unauthorized"],
    [404, "weather_not_found"],
    [500, "weather_failed"],
  ])("maps HTTP %s to %s", async (status, expected) => {
    const { getCurrentWeather } = await import("@ai/tools/server/weather");
    mockFetchWithRetry.mockResolvedValue(new Response("nope", { status }));

    const execute = getCurrentWeather.execute;
    if (!execute) throw new Error("getCurrentWeather.execute is undefined");

    await expect(
      execute(
        {
          city: "Paris",
          coordinates: null,
          fresh: true,
          lang: null,
          units: "metric",
          zip: null,
        },
        mockContext
      )
    ).rejects.toMatchObject({ code: expected });
  });
});
