/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  setRateLimitFactoryForTests,
  setSupabaseFactoryForTests,
} from "@/lib/api/factory";
import { stubRateLimitDisabled } from "@/test/helpers/env";
import {
  createMockNextRequest,
  createRouteParamsContext,
  getMockCookiesForTest,
} from "@/test/helpers/route";

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () =>
    getMockCookiesForTest({ "sb-access-token": "test-token" })
  ),
}));

// Import after mocks are registered
import { GET as getUpcomingFlights } from "../upcoming/route";

describe("/api/flights/upcoming", () => {
  const supabaseClient = {
    auth: {
      getUser: vi.fn(),
    },
    from: vi.fn(),
  } as {
    auth: { getUser: ReturnType<typeof vi.fn> };
    from: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    stubRateLimitDisabled();
    setRateLimitFactoryForTests(async () => ({
      limit: 30,
      remaining: 29,
      reset: Date.now() + 60_000,
      success: true,
    }));
    setSupabaseFactoryForTests(async () => supabaseClient as never);
    supabaseClient.auth.getUser.mockResolvedValue({
      data: { user: { id: "user-1" } },
      error: null,
    });
    supabaseClient.from.mockReset();
  });

  afterEach(() => {
    setRateLimitFactoryForTests(null);
    setSupabaseFactoryForTests(null);
    vi.clearAllMocks();
  });

  it("maps upcoming flights from Supabase rows", async () => {
    type FlightQueryBuilder = {
      select: ReturnType<typeof vi.fn>;
      eq: ReturnType<typeof vi.fn>;
      gte: ReturnType<typeof vi.fn>;
      order: ReturnType<typeof vi.fn>;
      limit: ReturnType<typeof vi.fn>;
      returns: ReturnType<typeof vi.fn>;
    };

    const builder: FlightQueryBuilder = (() => {
      const returns = vi.fn(async () => ({
        data: [
          {
            airline: "DL",
            currency: "USD",
            departure_date: "2026-01-20T10:00:00.000Z",
            destination: "JFK",
            flight_class: "economy",
            flight_number: "DL123",
            id: 1,
            metadata: {
              airlineName: "Delta",
              arrivalTime: "2026-01-20T18:00:00.000Z",
              duration: 480,
              gate: "A1",
              seatsAvailable: 2,
              status: "delayed",
              stops: 1,
              terminal: "2",
              tripName: "NYC Sprint",
            },
            origin: "SFO",
            price: 399,
            return_date: null,
            trip_id: 42,
          },
        ],
        error: null,
      }));

      const builderRef: FlightQueryBuilder = {
        eq: vi.fn(() => builderRef),
        gte: vi.fn(() => builderRef),
        limit: vi.fn(() => builderRef),
        order: vi.fn(() => builderRef),
        returns,
        select: vi.fn(() => builderRef),
      };

      return builderRef;
    })();

    supabaseClient.from.mockReturnValue(builder);

    const req = createMockNextRequest({
      method: "GET",
      searchParams: { limit: "1" },
      url: "http://localhost/api/flights/upcoming",
    });

    const res = await getUpcomingFlights(req, createRouteParamsContext());
    const body = (await res.json()) as Array<Record<string, unknown>>;

    expect(res.status).toBe(200);
    expect(body).toHaveLength(1);
    expect(body[0]).toMatchObject({
      airline: "DL",
      airlineName: "Delta",
      arrivalTime: "2026-01-20T18:00:00.000Z",
      cabinClass: "economy",
      currency: "USD",
      departureTime: "2026-01-20T10:00:00.000Z",
      destination: "JFK",
      duration: 480,
      flightNumber: "DL123",
      gate: "A1",
      origin: "SFO",
      price: 399,
      seatsAvailable: 2,
      status: "delayed",
      stops: 1,
      terminal: "2",
      tripId: "42",
      tripName: "NYC Sprint",
    });
  });

  it("returns 500 when Supabase query fails", async () => {
    type FlightQueryBuilder = {
      select: ReturnType<typeof vi.fn>;
      eq: ReturnType<typeof vi.fn>;
      gte: ReturnType<typeof vi.fn>;
      order: ReturnType<typeof vi.fn>;
      limit: ReturnType<typeof vi.fn>;
      returns: ReturnType<typeof vi.fn>;
    };

    const builder: FlightQueryBuilder = (() => {
      const returns = vi.fn(async () => ({
        data: null,
        error: new Error("boom"),
      }));

      const builderRef: FlightQueryBuilder = {
        eq: vi.fn(() => builderRef),
        gte: vi.fn(() => builderRef),
        limit: vi.fn(() => builderRef),
        order: vi.fn(() => builderRef),
        returns,
        select: vi.fn(() => builderRef),
      };

      return builderRef;
    })();

    supabaseClient.from.mockReturnValue(builder);

    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/flights/upcoming",
    });

    const res = await getUpcomingFlights(req, createRouteParamsContext());
    const body = (await res.json()) as { error?: string };

    expect(res.status).toBe(500);
    expect(body.error).toBe("upcoming_flights_failed");
  });
});
