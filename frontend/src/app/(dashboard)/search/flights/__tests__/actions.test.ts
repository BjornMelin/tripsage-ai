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
const { submitFlightSearch } = await import("../actions");

describe("submitFlightSearch server action", () => {
  it("validates and returns valid flight search params", async () => {
    const params = {
      adults: 2,
      cabinClass: "economy" as const,
      departureDate: "2025-06-15",
      destination: "LHR",
      origin: "JFK",
      returnDate: "2025-06-22",
    };

    const result = await submitFlightSearch(params);

    expect(result).toEqual(params);
  });

  it("validates params with optional fields omitted", async () => {
    const params = {
      adults: 1,
      destination: "LAX",
      origin: "NYC",
    };

    const result = await submitFlightSearch(params);

    expect(result.origin).toBe("NYC");
    expect(result.destination).toBe("LAX");
    expect(result.adults).toBe(1);
  });

  it("throws error for invalid cabin class", async () => {
    const params = {
      cabinClass: "invalid-class" as "economy",
      destination: "LHR",
      origin: "JFK",
    };

    await expect(submitFlightSearch(params)).rejects.toThrow(
      /Invalid flight search params/
    );
  });

  it("validates passengers with nested structure", async () => {
    const params = {
      destination: "CDG",
      origin: "LAX",
      passengers: {
        adults: 2,
        children: 1,
        infants: 0,
      },
    };

    const result = await submitFlightSearch(params);

    expect(result.passengers?.adults).toBe(2);
    expect(result.passengers?.children).toBe(1);
    expect(result.passengers?.infants).toBe(0);
  });
});
