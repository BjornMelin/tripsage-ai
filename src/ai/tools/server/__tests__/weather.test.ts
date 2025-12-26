/** @vitest-environment node */

import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { server } from "@/test/msw/server";
import { withFakeTimers } from "@/test/utils/with-fake-timers";

const mockGetServerEnvVar = vi.hoisted(() => vi.fn());

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

async function getWeatherExecute() {
  const { getCurrentWeather } = await import("@ai/tools/server/weather");
  const execute = getCurrentWeather.execute;
  if (!execute) throw new Error("getCurrentWeather.execute is undefined");
  return execute;
}

function isAsyncIterable(value: unknown): value is AsyncIterable<unknown> {
  return (
    typeof value === "object" &&
    value !== null &&
    Symbol.asyncIterator in value &&
    typeof (value as { [Symbol.asyncIterator]?: unknown })[Symbol.asyncIterator] ===
      "function"
  );
}

describe("getCurrentWeather", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetServerEnvVar.mockReturnValue("test-key");
  });

  test("builds correct URL for city query and maps response fields", async () => {
    const execute = await getWeatherExecute();
    let lastRequestUrl: URL | undefined;
    server.use(
      http.get("https://api.openweathermap.org/data/2.5/weather", ({ request }) => {
        lastRequestUrl = new URL(request.url);
        return HttpResponse.json({
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
        });
      })
    );

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

    expect(lastRequestUrl?.toString()).toContain(
      "https://api.openweathermap.org/data/2.5/weather"
    );
    expect(lastRequestUrl?.searchParams.get("q")).toBe("Paris");
    expect(lastRequestUrl?.searchParams.get("units")).toBe("metric");
    expect(lastRequestUrl?.searchParams.get("lang")).toBe("en");
    expect(lastRequestUrl?.searchParams.get("appid")).toBe("test-key");

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
    const execute = await getWeatherExecute();
    let lastRequestUrl: URL | undefined;
    server.use(
      http.get("https://api.openweathermap.org/data/2.5/weather", ({ request }) => {
        lastRequestUrl = new URL(request.url);
        return HttpResponse.json({ main: { temp: 20 }, name: "X" });
      })
    );

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

    expect(lastRequestUrl?.searchParams.get("lat")).toBe("48.8566");
    expect(lastRequestUrl?.searchParams.get("lon")).toBe("2.3522");
  });

  test("uses zip when provided", async () => {
    const execute = await getWeatherExecute();
    let lastRequestUrl: URL | undefined;
    server.use(
      http.get("https://api.openweathermap.org/data/2.5/weather", ({ request }) => {
        lastRequestUrl = new URL(request.url);
        return HttpResponse.json({ main: { temp: 20 }, name: "X" });
      })
    );

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

    expect(lastRequestUrl?.searchParams.get("zip")).toBe("10001");
  });

  test("fails closed when not configured", async () => {
    const execute = await getWeatherExecute();
    mockGetServerEnvVar.mockImplementation(() => {
      throw new Error("Missing env OPENWEATHERMAP_API_KEY");
    });

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

  test(
    "maps fetch_timeout to weather_timeout",
    withFakeTimers(async () => {
      const execute = await getWeatherExecute();
      server.use(
        http.get(
          "https://api.openweathermap.org/data/2.5/weather",
          () => new Promise<Response>(() => undefined)
        )
      );

      const pendingRequest: Promise<unknown> = Promise.resolve(
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
      );

      pendingRequest.catch(() => undefined);

      await vi.advanceTimersByTimeAsync(12_500);

      await expect(pendingRequest).rejects.toMatchObject({ code: "weather_timeout" });
    })
  );

  test(
    "maps fetch_failed to weather_failed",
    withFakeTimers(async () => {
      const execute = await getWeatherExecute();
      server.use(
        http.get("https://api.openweathermap.org/data/2.5/weather", () => {
          throw new Error("Network error");
        })
      );

      const pendingRequest: Promise<unknown> = Promise.resolve(
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
      );

      pendingRequest.catch(() => undefined);

      await vi.advanceTimersByTimeAsync(2_000);

      await expect(pendingRequest).rejects.toMatchObject({ code: "weather_failed" });
    })
  );

  test.each([
    [429, "weather_rate_limited"],
    [401, "weather_unauthorized"],
    [404, "weather_not_found"],
    [500, "weather_failed"],
  ])("maps HTTP %s to %s", async (status, expected) => {
    const execute = await getWeatherExecute();
    server.use(
      http.get("https://api.openweathermap.org/data/2.5/weather", () => {
        return new HttpResponse("nope", { status });
      })
    );

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
