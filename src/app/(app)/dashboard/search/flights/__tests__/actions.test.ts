/** @vitest-environment node */

import type { FlightSearchParams } from "@schemas/search";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { unsafeCast } from "@/test/helpers/unsafe-cast";

// Mock telemetry span (must include recordTelemetryEvent as logger.ts imports it)
vi.mock("@/lib/telemetry/span", () => ({
  recordTelemetryEvent: vi.fn(),
  withTelemetrySpan: vi.fn(
    async <T>(_name: string, _options: unknown, fn: () => T | Promise<T>): Promise<T> =>
      await fn()
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
        destination: destination.toLowerCase(),
        origin: origin.toLowerCase(),
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

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.data).toEqual({
        ...params,
        passengers: { adults: 2, children: 0, infants: 0 },
      });
    }
    expectTelemetrySpanCalled("JFK", "LHR");
  });

  it("validates params with optional fields omitted", async () => {
    const params = {
      adults: 1,
      destination: "LAX",
      origin: "NYC",
    };

    const result = await submitFlightSearch(params);

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.data).toEqual({
        ...params,
        cabinClass: "economy", // schema default
        passengers: { adults: 1, children: 0, infants: 0 }, // normalized defaults
      });
    }
    expectTelemetrySpanCalled("NYC", "LAX");
  });

  it("returns error for invalid cabin class", async () => {
    const params = {
      cabinClass: "invalid-class",
      destination: "LHR",
      origin: "JFK",
    };

    const result = await submitFlightSearch(unsafeCast<FlightSearchParams>(params));
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.error).toBe("invalid_request");
      expect(result.error.reason).toBe("Invalid flight search parameters");
      expect(result.error.issues).toBeDefined();

      const issues = result.error.issues ?? [];
      expect(issues.length).toBeGreaterThan(0);
      expect(issues.some((issue) => issue.path.join(".") === "cabinClass")).toBe(true);
      expect(result.error.fieldErrors?.cabinClass).toBeDefined();
    }
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

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.data.passengers?.adults).toBe(2);
      expect(result.data.passengers?.children).toBe(1);
      expect(result.data.passengers?.infants).toBe(0);
    }
    expectTelemetrySpanCalled("LAX", "CDG");
  });
});
