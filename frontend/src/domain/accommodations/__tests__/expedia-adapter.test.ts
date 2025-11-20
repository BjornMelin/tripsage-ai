import { beforeEach, describe, expect, type Mock, test, vi } from "vitest";

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: (
    _name: string,
    _opts: unknown,
    fn: (span: Record<string, unknown>) => unknown
  ) =>
    fn({
      addEvent: vi.fn(),
      end: vi.fn(),
      recordException: vi.fn(),
      setAttribute: vi.fn(),
    }),
}));

vi.mock("@domain/expedia/client", () => {
  const client = {
    checkAvailability: vi.fn(),
    createBooking: vi.fn(),
    getPropertyDetails: vi.fn(),
    priceCheck: vi.fn(),
    searchAvailability: vi.fn(),
  };

  class ExpediaApiError extends Error {
    statusCode?: number;
    constructor(message: string, _code: string, statusCode?: number) {
      super(message);
      this.statusCode = statusCode;
    }
  }

  return {
    ExpediaApiError,
    getExpediaClient: () => client,
  };
});

vi.mock("@/lib/http/retry", () => ({
  retryWithBackoff: async (fn: (attempt: number) => unknown) => {
    try {
      return await fn(1);
    } catch (_error) {
      return await fn(2);
    }
  },
}));

import { ExpediaProviderAdapter } from "@domain/accommodations/providers/expedia-adapter";
import type { AccommodationProviderAdapter } from "@domain/accommodations/providers/types";
import { ExpediaApiError, getExpediaClient } from "@domain/expedia/client";

const mockedClient = getExpediaClient() as unknown as Record<string, Mock>;

describe("ExpediaProviderAdapter", () => {
  let adapter: AccommodationProviderAdapter;

  beforeEach(() => {
    vi.clearAllMocks();
    adapter = new ExpediaProviderAdapter({
      breaker: { cooldownMs: 10, failureThreshold: 2 },
      retry: { attempts: 2, baseDelayMs: 1, maxDelayMs: 2 },
    });
  });

  test("retries on 429 and succeeds", async () => {
    mockedClient.searchAvailability
      .mockRejectedValueOnce(new ExpediaApiError("rate", "RATE_LIMIT", 429))
      .mockResolvedValueOnce({ properties: [] });

    const result = await adapter.searchAvailability(
      {
        checkIn: "2025-01-01",
        checkOut: "2025-01-02",
        currency: "USD",
        guests: 1,
        propertyIds: ["p1"],
      },
      { sessionId: "s1" }
    );

    expect(result.ok).toBe(true);
    expect(mockedClient.searchAvailability).toHaveBeenCalledTimes(2);
  });

  test("opens circuit after threshold", async () => {
    mockedClient.searchAvailability.mockRejectedValue(
      new ExpediaApiError("server", "SERVER", 503)
    );

    const payload = {
      checkIn: "2025-01-01",
      checkOut: "2025-01-02",
      currency: "USD",
      guests: 1,
      propertyIds: ["p1"],
    };

    const first = await adapter.searchAvailability(payload, { sessionId: "s1" });
    const second = await adapter.searchAvailability(payload, { sessionId: "s1" });
    const third = await adapter.searchAvailability(payload, { sessionId: "s1" });

    expect(first.ok).toBe(false);
    expect(second.ok).toBe(false);
    expect(third.ok).toBe(false);
    if (third.ok) {
      throw new Error("expected circuit to be open");
    }
    expect(third.error.code).toBe("circuit_open");
  });
});
