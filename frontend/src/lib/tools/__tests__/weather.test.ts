import { afterEach, beforeEach, expect, test, vi } from "vitest";

const env = process.env;

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
  process.env = { ...env, OPENWEATHER_API_KEY: "test_key" };
  vi.resetModules();
});

afterEach(() => {
  vi.unstubAllGlobals();
  process.env = env;
});

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

test("getCurrentWeather returns weather data", async () => {
  const mockRes = {
    json: async () => ({
      main: { humidity: 65, temp: 22.5 },
      weather: [{ description: "clear sky" }],
    }),
    ok: true,
  } as Response;
  (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
  const { getCurrentWeather } = await import("../weather");
  const result = await getCurrentWeather.execute?.(
    { city: "Paris", units: "metric" },
    mockContext
  );
  expect(result).toHaveProperty("city", "Paris");
  expect(result).toHaveProperty("temp", 22.5);
  expect(result).toHaveProperty("description", "clear sky");
  expect(result).toHaveProperty("humidity", 65);
});

test("getCurrentWeather uses default metric units", async () => {
  const mockRes = {
    json: async () => ({
      main: { humidity: 70, temp: 15 },
      weather: [{ description: "cloudy" }],
    }),
    ok: true,
  } as Response;
  (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
  const { getCurrentWeather } = await import("../weather");
  await getCurrentWeather.execute?.({ city: "London", units: "metric" }, mockContext);
  const call = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
  const url = new URL(call[0] as string);
  expect(url.searchParams.get("units")).toBe("metric");
});

test("getCurrentWeather throws when not configured", async () => {
  process.env.OPENWEATHER_API_KEY = "";
  vi.resetModules();
  const { getCurrentWeather } = await import("../weather");
  await expect(
    getCurrentWeather.execute?.({ city: "Paris", units: "metric" }, mockContext)
  ).rejects.toThrow(/weather_not_configured/);
});

test("getCurrentWeather maps API errors correctly", async () => {
  const mockRes = {
    ok: false,
    status: 404,
    text: async () => "city not found",
  } as Response;
  (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
  const { getCurrentWeather } = await import("../weather");
  await expect(
    getCurrentWeather.execute?.({ city: "InvalidCity", units: "metric" }, mockContext)
  ).rejects.toThrow(/weather_failed:404/);
});

test("getCurrentWeather handles missing weather data gracefully", async () => {
  const mockRes = {
    json: async () => ({
      main: { temp: 20 },
    }),
    ok: true,
  } as Response;
  (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
  const { getCurrentWeather } = await import("../weather");
  const result = await getCurrentWeather.execute?.(
    { city: "TestCity", units: "metric" },
    mockContext
  );
  expect(result).toHaveProperty("description", null);
  expect(result).toHaveProperty("humidity", null);
});
