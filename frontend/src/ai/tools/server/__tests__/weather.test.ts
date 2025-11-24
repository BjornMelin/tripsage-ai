/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { canonicalizeParamsForCache } from "@/lib/cache/keys";

vi.mock("@/lib/http/fetch-retry", () => ({
  fetchWithRetry: vi.fn(),
}));

vi.mock("@/lib/cache/upstash", () => ({
  getCachedJson: vi.fn().mockResolvedValue(null),
  setCachedJson: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn((_name: string, _options, fn) =>
    fn({
      addEvent: vi.fn(),
      setAttribute: vi.fn(),
    })
  ),
}));

vi.mock("@/lib/env/server", () => ({
  getServerEnvVar: vi.fn(() => "test_key"),
}));

// Shared test fixtures
const _mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

const _createMockResponse = (data: Record<string, unknown>) =>
  ({
    json: async () => data,
    ok: true,
    status: 200,
    text: async () => JSON.stringify(data),
  }) as Response;

const _fullWeatherResponse = {
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

const _minimalWeatherResponse = {
  main: { temp: 20 },
  name: "Paris",
  weather: [{ description: "sunny" }],
};

beforeEach(async () => {
  vi.clearAllMocks();
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
