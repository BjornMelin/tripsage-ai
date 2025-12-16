/** @vitest-environment node */

import { searchFlights } from "@ai/tools";
import type { FlightSearchResult } from "@schemas/flights";
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { buildUpstashCacheMock } from "@/test/mocks/cache";
import { server } from "@/test/msw/server";

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

vi.mock("@/lib/cache/upstash", async () => {
  const { buildUpstashCacheMock: factory } = await import("@/test/mocks/cache");
  const cache = factory();
  (globalThis as Record<string, unknown>).__upstashCache = cache;
  return cache.module;
});

function getUpstashCache(): ReturnType<typeof buildUpstashCacheMock> {
  return (globalThis as Record<string, unknown>).__upstashCache as ReturnType<
    typeof buildUpstashCacheMock
  >;
}

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: vi.fn((_name, _options, fn) =>
    fn({
      addEvent: vi.fn(),
      setAttribute: vi.fn(),
    })
  ),
}));

vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => undefined),
}));

const duffelKeyState: { value: string | undefined } = { value: "test_duffel_key" };

vi.mock("@/lib/env/server", () => {
  const getServerEnvVarWithFallback = vi.fn((key: string) => {
    if (key === "DUFFEL_ACCESS_TOKEN" || key === "DUFFEL_API_KEY") {
      return duffelKeyState.value;
    }
    return undefined;
  });
  return {
    getServerEnvVarWithFallback,
    setMockDuffelKey: (value?: string) => {
      duffelKeyState.value = value;
    },
  };
});

describe("searchFlights tool", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    duffelKeyState.value = "test_duffel_key";
    getUpstashCache().reset();
  });

  it("submits Duffel offer requests with normalized payload", async () => {
    const captured = {
      authorization: null as string | null,
      body: null as unknown,
      duffelVersion: null as string | null,
    };

    server.use(
      http.post("https://api.duffel.com/air/offer_requests", async ({ request }) => {
        captured.body = await request.json();
        captured.authorization = request.headers.get("authorization");
        captured.duffelVersion = request.headers.get("duffel-version");
        return HttpResponse.json({ data: { offers: [{ id: "offer-1" }] } });
      })
    );

    const result = (await searchFlights.execute?.(
      {
        cabinClass: "economy",
        currency: "USD",
        departureDate: "2025-03-10",
        destination: "JFK",
        origin: "SFO",
        passengers: 2,
      },
      mockContext
    )) as unknown as FlightSearchResult;

    expect(captured.authorization).toBe("Bearer test_duffel_key");
    expect(captured.duffelVersion).toBe("v2");
    expect(captured.body).toMatchObject({
      cabin_class: "economy",
      payment_currency: "USD",
      return_offers: true,
    });
    expect(result).toMatchObject({ currency: "USD" });
    expect(Array.isArray(result?.offers)).toBe(true);
  });

  it("throws when Duffel credentials are missing", async () => {
    const envModule = (await import("@/lib/env/server")) as unknown as {
      setMockDuffelKey: (value?: string) => void;
    };
    envModule.setMockDuffelKey(undefined);
    await expect(
      searchFlights.execute?.(
        {
          cabinClass: "economy",
          currency: "USD",
          departureDate: "2025-03-10",
          destination: "JFK",
          origin: "SFO",
          passengers: 1,
        },
        mockContext
      )
    ).rejects.toThrow(/Duffel API key is not configured/);
    envModule.setMockDuffelKey("test_duffel_key");
  });

  it("bubbles up Duffel API errors", async () => {
    server.use(
      http.post("https://api.duffel.com/air/offer_requests", () => {
        return HttpResponse.text("server_error", { status: 500 });
      })
    );
    const envModule = (await import("@/lib/env/server")) as unknown as {
      setMockDuffelKey: (value?: string) => void;
    };
    envModule.setMockDuffelKey("test_duffel_key");

    await expect(
      searchFlights.execute?.(
        {
          cabinClass: "economy",
          currency: "USD",
          departureDate: "2025-03-10",
          destination: "JFK",
          origin: "SFO",
          passengers: 1,
        },
        mockContext
      )
    ).rejects.toThrow(/duffel_offer_request_failed:500/);
  });
});
