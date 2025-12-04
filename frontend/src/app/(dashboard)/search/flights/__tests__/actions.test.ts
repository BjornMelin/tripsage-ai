/** @vitest-environment node */

import type { FlightSearchParams } from "@schemas/search";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock telemetry span
vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn(
    async <T>(_name: string, _options: unknown, fn: () => Promise<T>): Promise<T> =>
      fn()
  ),
}));

// Dynamic import after mocks
const { withTelemetrySpan } = await import("@/lib/telemetry/span");
const { submitFlightSearch } = await import("../actions");

const withTelemetrySpanMock = vi.mocked(withTelemetrySpan);

const expectTelemetrySpanCalled = (origin: string, destination: string) => {
  expect(withTelemetrySpanMock).toHaveBeenCalledWith(
    "search.flight.server.submit",
    expect.objectContaining({
      attributes: expect.objectContaining({
        destination,
        origin,
        searchType: "flight",
      }),
    }),
    expect.any(Function)
  );
};

// Ensure mocks reset between tests
beforeEach(() => {
  vi.clearAllMocks();
});

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

    expect(result).toEqual({
      ...params,
      passengers: { adults: 2, children: 0, infants: 0 },
    });
    expectTelemetrySpanCalled("JFK", "LHR");
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
    // Defaults applied for omitted optional fields
    expect(result.cabinClass).toBe("economy");
    expect(result.passengers).toEqual({ adults: 1, children: 0, infants: 0 });
    expectTelemetrySpanCalled("NYC", "LAX");
  });

  it("throws error for invalid cabin class", async () => {
    const params = {
      cabinClass: "invalid-class",
      destination: "LHR",
      origin: "JFK",
    };

    await expect(
      submitFlightSearch(params as unknown as FlightSearchParams)
    ).rejects.toThrow(/Invalid flight search params/);
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
    expectTelemetrySpanCalled("LAX", "CDG");
  });
});
