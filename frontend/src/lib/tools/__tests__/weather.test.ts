import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";
import { fetchWithRetry } from "@/lib/http/fetch-retry";
import { getRedis } from "@/lib/redis";
import { WEATHER_CACHE_TTL_SECONDS } from "../constants";
import { getCurrentWeather } from "../weather";

vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(),
}));

vi.mock("@/lib/http/fetch-retry", () => ({
  fetchWithRetry: vi.fn(),
}));

vi.mock("@/lib/env/server", () => ({
  getServerEnvVar: vi.fn(() => "test_key"),
}));

// Shared test fixtures
const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

const createMockResponse = (data: Record<string, unknown>) =>
  ({
    json: async () => data,
    ok: true,
    status: 200,
    text: async () => JSON.stringify(data),
  }) as Response;

const fullWeatherResponse = {
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
  sys: {
    country: "FR",
    sunrise: 1234567890,
    sunset: 1234567890,
  },
  timezone: 3600,
  visibility: 10000,
  weather: [
    {
      description: "clear sky",
      icon: "01d",
      id: 800,
      main: "Clear",
    },
  ],
  wind: { deg: 180, gust: 5.2, speed: 3.5 },
};

const minimalWeatherResponse = {
  main: { temp: 20 },
  name: "Paris",
  weather: [{ description: "sunny" }],
};

beforeEach(async () => {
  vi.clearAllMocks();
  (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(null);
  const { getServerEnvVar } = await import("@/lib/env/server");
  (getServerEnvVar as ReturnType<typeof vi.fn>).mockReturnValue("test_key");
});

afterEach(() => {
  vi.clearAllMocks();
});

// ---- FAST SYNCHRONOUS TESTS (run first) ------------------------------------

describe("cache key generation", () => {
  test("generates consistent cache keys for same parameters", () => {
    const params = { lang: "en", q: "Paris", units: "metric" };
    const key1 = canonicalizeParamsForCache(params, "weather");
    const key2 = canonicalizeParamsForCache(params, "weather");
    expect(key1).toBe(key2);
  });

  test.each([
    ["different cities", { q: "Paris" }, { q: "London" }],
    [
      "different units",
      { q: "Paris", units: "metric" },
      { q: "Paris", units: "imperial" },
    ],
    ["different ZIP codes", { zip: "10001" }, { zip: "90210" }],
    [
      "different coordinates",
      { lat: 48.8566, lon: 2.3522 },
      { lat: 51.5074, lon: -0.1278 },
    ],
    ["different languages", { lang: "en", q: "Paris" }, { lang: "fr", q: "Paris" }],
  ])("generates different cache keys for %s", (_label, params1, params2) => {
    const baseParams1 = {
      ...params1,
      units: ("units" in params1 ? params1.units : "metric") as "metric" | "imperial",
    };
    const baseParams2 = {
      ...params2,
      units: ("units" in params2 ? params2.units : "metric") as "metric" | "imperial",
    };
    const key1 = canonicalizeParamsForCache(baseParams1, "weather");
    const key2 = canonicalizeParamsForCache(baseParams2, "weather");
    expect(key1).not.toBe(key2);
  });
});

describe("input validation", () => {
  test("requires either city, coordinates, or zip", async () => {
    await expect(
      getCurrentWeather.execute?.({ units: "metric" }, mockContext)
    ).rejects.toThrow(/Either city, coordinates, or zip must be provided/);
  });

  test.each([
    ["city too short", { city: "A", units: "metric" as const }],
    [
      "invalid latitude",
      { coordinates: { lat: 91, lon: 0 }, units: "metric" as const },
    ],
    [
      "invalid longitude",
      { coordinates: { lat: 0, lon: 181 }, units: "metric" as const },
    ],
    ["invalid language code", { city: "Paris", lang: "eng", units: "metric" as const }],
  ])("rejects %s", async (_label, params) => {
    await expect(getCurrentWeather.execute?.(params, mockContext)).rejects.toThrow();
  });
});

// ---- CORE FUNCTIONALITY TESTS ----------------------------------------------

describe("getCurrentWeather", () => {
  test("returns complete weather data with all fields", async () => {
    (fetchWithRetry as ReturnType<typeof vi.fn>).mockResolvedValue(
      createMockResponse(fullWeatherResponse)
    );

    const result = await getCurrentWeather.execute?.(
      { city: "Paris", units: "metric" },
      mockContext
    );

    // Basic fields
    expect(result).toMatchObject({
      city: "Paris",
      country: "FR",
      description: "clear sky",
      feelsLike: 21.8,
      fromCache: false,
      humidity: 65,
      pressure: 1013,
      provider: "http_get",
      status: "success",
      temp: 22.5,
      visibility: 10000,
      windDirection: 180,
      windSpeed: 3.5,
    });

    // Extended fields
    expect(result).toMatchObject({
      clouds: 20,
      icon: "01d",
      rain: 0.5,
      snow: 0.2,
      sunrise: 1234567890,
      sunset: 1234567890,
      tempMax: 25.0,
      tempMin: 20.0,
      timezone: 3600,
      windGust: 5.2,
    });

    if (result && typeof result === "object" && "tookMs" in result) {
      expect(typeof result.tookMs).toBe("number");
    }
  });

  test.each([
    ["city", { city: "Paris" }],
    ["coordinates", { coordinates: { lat: 48.8566, lon: 2.3522 } }],
    ["ZIP code", { zip: "10001" }],
  ])("supports %s lookup", async (_label, params) => {
    (fetchWithRetry as ReturnType<typeof vi.fn>).mockResolvedValue(
      createMockResponse(minimalWeatherResponse)
    );

    await getCurrentWeather.execute?.(
      { ...params, units: "metric" as const },
      mockContext
    );

    const call = (fetchWithRetry as ReturnType<typeof vi.fn>).mock.calls[0];
    const url = new URL(call[0] as string);
    expect(url.searchParams.get("appid")).toBe("test_key");

    if ("city" in params) {
      expect(url.searchParams.get("q")).toBe("Paris");
    } else if ("coordinates" in params) {
      expect(url.searchParams.get("lat")).toBe("48.8566");
      expect(url.searchParams.get("lon")).toBe("2.3522");
    } else if ("zip" in params) {
      expect(url.searchParams.get("zip")).toBe("10001");
    }
  });

  test.each([
    ["metric", "metric" as const],
    ["imperial", "imperial" as const],
  ])("supports %s units", async (_label, units) => {
    (fetchWithRetry as ReturnType<typeof vi.fn>).mockResolvedValue(
      createMockResponse(minimalWeatherResponse)
    );

    await getCurrentWeather.execute?.({ city: "Paris", units }, mockContext);

    const call = (fetchWithRetry as ReturnType<typeof vi.fn>).mock.calls[0];
    const url = new URL(call[0] as string);
    expect(url.searchParams.get("units")).toBe(units);
  });

  test("supports language parameter", async () => {
    (fetchWithRetry as ReturnType<typeof vi.fn>).mockResolvedValue(
      createMockResponse({
        ...minimalWeatherResponse,
        weather: [{ description: "ciel dégagé" }],
      })
    );

    await getCurrentWeather.execute?.(
      { city: "Paris", lang: "fr", units: "metric" },
      mockContext
    );

    const call = (fetchWithRetry as ReturnType<typeof vi.fn>).mock.calls[0];
    const url = new URL(call[0] as string);
    expect(url.searchParams.get("lang")).toBe("fr");
  });

  test("trims whitespace from city and ZIP", async () => {
    (fetchWithRetry as ReturnType<typeof vi.fn>).mockResolvedValue(
      createMockResponse(minimalWeatherResponse)
    );

    // Test city trimming
    await getCurrentWeather.execute?.(
      { city: "  Paris  ", units: "metric" },
      mockContext
    );
    let call = (fetchWithRetry as ReturnType<typeof vi.fn>).mock.calls[0];
    let url = new URL(call[0] as string);
    expect(url.searchParams.get("q")).toBe("Paris");

    // Test ZIP trimming
    await getCurrentWeather.execute?.(
      { units: "metric", zip: "  10001  " },
      mockContext
    );
    call = (fetchWithRetry as ReturnType<typeof vi.fn>).mock.calls[1];
    url = new URL(call[0] as string);
    expect(url.searchParams.get("zip")).toBe("10001");
  });
});

// ---- FIELD EXTRACTION TESTS -------------------------------------------------

describe("field extraction", () => {
  test("extracts precipitation data (rain 1h and 3h, snow)", async () => {
    (fetchWithRetry as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce(
        createMockResponse({ ...minimalWeatherResponse, rain: { "1h": 2.5 } })
      )
      .mockResolvedValueOnce(
        createMockResponse({ ...minimalWeatherResponse, rain: { "3h": 5.0 } })
      )
      .mockResolvedValueOnce(
        createMockResponse({ ...minimalWeatherResponse, snow: { "1h": 1.5 } })
      );

    const result1 = await getCurrentWeather.execute?.(
      { city: "London", units: "metric" },
      mockContext
    );
    expect(result1).toHaveProperty("rain", 2.5);

    const result2 = await getCurrentWeather.execute?.(
      { city: "London", units: "metric" },
      mockContext
    );
    expect(result2).toHaveProperty("rain", 5.0);

    const result3 = await getCurrentWeather.execute?.(
      { city: "Oslo", units: "metric" },
      mockContext
    );
    expect(result3).toHaveProperty("snow", 1.5);
  });

  test("handles missing optional fields gracefully", async () => {
    (fetchWithRetry as ReturnType<typeof vi.fn>).mockResolvedValue(
      createMockResponse(minimalWeatherResponse)
    );

    const result = await getCurrentWeather.execute?.(
      { city: "Paris", units: "metric" },
      mockContext
    );

    expect(result).toMatchObject({
      clouds: null,
      country: undefined,
      icon: null,
      rain: null,
      snow: null,
      tempMax: null,
      tempMin: null,
      timezone: undefined,
      windGust: null,
    });
  });
});

// ---- ERROR HANDLING TESTS --------------------------------------------------

describe("error handling", () => {
  test("throws when API key not configured", async () => {
    const { getServerEnvVar } = await import("@/lib/env/server");
    (getServerEnvVar as ReturnType<typeof vi.fn>).mockImplementation(() => {
      throw new Error("OPENWEATHERMAP_API_KEY is not defined");
    });
    vi.resetModules();
    const { getCurrentWeather: freshTool } = await import("../weather");

    await expect(
      freshTool.execute?.({ city: "Paris", units: "metric" }, mockContext)
    ).rejects.toThrow(/weather_not_configured/);

    // Restore mock
    (getServerEnvVar as ReturnType<typeof vi.fn>).mockReturnValue("test_key");
    vi.resetModules();
  });

  test("maps timeout errors correctly", async () => {
    const timeoutError: Error & { code?: string } = new Error("fetch_timeout");
    timeoutError.code = "fetch_timeout";
    (fetchWithRetry as ReturnType<typeof vi.fn>).mockRejectedValue(timeoutError);

    await expect(
      getCurrentWeather.execute?.({ city: "Paris", units: "metric" }, mockContext)
    ).rejects.toThrow(/weather_timeout/);
  });

  test.each([
    [401, "weather_unauthorized"],
    [404, "weather_not_found"],
    [429, "weather_rate_limited"],
  ])("maps HTTP %d to %s", async (status, errorCode) => {
    (fetchWithRetry as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status,
      text: async () => `Error ${status}`,
    } as Response);

    await expect(
      getCurrentWeather.execute?.({ city: "Paris", units: "metric" }, mockContext)
    ).rejects.toThrow(new RegExp(errorCode));
  });
});

// ---- CACHING TESTS ----------------------------------------------------------

describe("caching", () => {
  test("returns cached result when available", async () => {
    const cachedResult = {
      city: "Paris",
      description: "clear sky",
      fromCache: false,
      humidity: 65,
      provider: "http_get",
      status: "success" as const,
      temp: 22.5,
      tookMs: 100,
    };
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue({
      get: vi.fn().mockResolvedValue(cachedResult),
      set: vi.fn(),
    });

    const result = await getCurrentWeather.execute?.(
      { city: "Paris", units: "metric" },
      mockContext
    );

    expect(result).toMatchObject({
      city: "Paris",
      fromCache: true,
      temp: 22.5,
    });
  });

  test("bypasses cache when fresh flag is set", async () => {
    const redisMock = {
      get: vi.fn(),
      set: vi.fn(),
    };
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(redisMock);
    (fetchWithRetry as ReturnType<typeof vi.fn>).mockResolvedValue(
      createMockResponse(minimalWeatherResponse)
    );

    await getCurrentWeather.execute?.(
      { city: "Paris", fresh: true, units: "metric" },
      mockContext
    );

    expect(redisMock.get).not.toHaveBeenCalled();
  });

  test("caches result after successful fetch", async () => {
    const redisMock = {
      get: vi.fn().mockResolvedValue(null),
      set: vi.fn(),
    };
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(redisMock);
    (fetchWithRetry as ReturnType<typeof vi.fn>).mockResolvedValue(
      createMockResponse(minimalWeatherResponse)
    );

    await getCurrentWeather.execute?.({ city: "Paris", units: "metric" }, mockContext);

    expect(redisMock.set).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        city: "Paris",
        status: "success",
      }),
      { ex: WEATHER_CACHE_TTL_SECONDS }
    );
  });
});
