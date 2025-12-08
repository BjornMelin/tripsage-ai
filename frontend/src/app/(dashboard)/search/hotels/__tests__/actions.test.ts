/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";

// Mock telemetry span
vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn(
    async <T>(_name: string, _options: unknown, fn: () => Promise<T>): Promise<T> =>
      fn()
  ),
}));

// Dynamic import after mocks
const { submitHotelSearch } = await import("../actions");

describe("submitHotelSearch server action", () => {
  it("validates and returns valid accommodation search params", async () => {
    const params = {
      adults: 2,
      checkIn: "2025-06-15",
      checkOut: "2025-06-18",
      destination: "Paris",
    };

    const result = await submitHotelSearch(params);

    expect(result).toEqual(params);
  });

  it("validates params with price range", async () => {
    const params = {
      adults: 1,
      checkIn: "2025-07-01",
      checkOut: "2025-07-05",
      destination: "London",
      priceRange: {
        max: 500,
        min: 100,
      },
    };

    const result = await submitHotelSearch(params);

    expect(result.priceRange?.min).toBe(100);
    expect(result.priceRange?.max).toBe(500);
  });

  it("validates params with amenities filter", async () => {
    const params = {
      amenities: ["wifi", "pool", "gym"],
      destination: "Miami",
    };

    const result = await submitHotelSearch(params);

    expect(result.amenities).toEqual(["wifi", "pool", "gym"]);
  });

  it("validates params with min rating", async () => {
    const params = {
      destination: "Tokyo",
      minRating: 4.5,
    };

    const result = await submitHotelSearch(params);

    expect(result.minRating).toBe(4.5);
  });

  it("throws error for invalid price range", async () => {
    const params = {
      destination: "Berlin",
      priceRange: {
        max: 100,
        min: 200, // min > max is invalid
      },
    };

    await expect(submitHotelSearch(params)).rejects.toThrow(
      /Invalid accommodation search params/
    );
  });

  it("throws error for invalid min rating", async () => {
    const params = {
      destination: "Sydney",
      minRating: 6, // max is 5
    };

    await expect(submitHotelSearch(params)).rejects.toThrow(
      /Invalid accommodation search params/
    );
  });
});
