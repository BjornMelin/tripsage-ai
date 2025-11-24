/** @vitest-environment node */

import { searchFlights } from "@ai/tools";
import type { FlightSearchResult } from "@schemas/flights";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

var upstashModule: {
  __reset?: () => void;
  deleteCachedJson: unknown;
  deleteCachedJsonMany: unknown;
  getCachedJson: unknown;
  setCachedJson: unknown;
};

vi.mock("@/lib/cache/upstash", () => {
  const store = new Map<string, string>();
  const getCachedJson = vi.fn(async (key: string) => {
    const val = store.get(key);
    return val ? (JSON.parse(val) as unknown) : null;
  });
  const setCachedJson = vi.fn(async (key: string, value: unknown) => {
    store.set(key, JSON.stringify(value));
  });
  const deleteCachedJson = vi.fn(async (key: string) => {
    store.delete(key);
  });
  const deleteCachedJsonMany = vi.fn(async (keys: string[]) => {
    let deleted = 0;
    keys.forEach((k) => {
      if (store.delete(k)) deleted += 1;
    });
    return deleted;
  });
  const reset = () => {
    store.clear();
    getCachedJson.mockReset();
    setCachedJson.mockReset();
    deleteCachedJson.mockReset();
    deleteCachedJsonMany.mockReset();
  };
  const module = {
    __reset: reset,
    deleteCachedJson,
    deleteCachedJsonMany,
    getCachedJson,
    setCachedJson,
  };
  upstashModule = module;
  return module;
});

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
    upstashModule?.__reset?.();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("submits Duffel offer requests with normalized payload", async () => {
    const mockOffers = [{ id: "offer-1" }];
    const fetchMock = vi.fn(async () => ({
      json: async () => ({ data: { offers: mockOffers } }),
      ok: true,
      status: 200,
    })) as unknown as typeof fetch;
    vi.stubGlobal("fetch", fetchMock);

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

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.duffel.com/air/offer_requests",
      expect.objectContaining({
        method: "POST",
      })
    );
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
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 500,
        text: async () => "server_error",
      })) as unknown as typeof fetch
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
