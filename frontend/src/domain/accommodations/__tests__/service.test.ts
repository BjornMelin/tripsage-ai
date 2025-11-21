import type { AccommodationProviderAdapter } from "@domain/accommodations/providers/types";
import { AccommodationsService } from "@domain/accommodations/service";
import { ACCOMMODATION_SEARCH_OUTPUT_SCHEMA } from "@schemas/accommodations";
import { beforeEach, describe, expect, type Mock, test, vi } from "vitest";
import type { TypedServerSupabase } from "@/lib/supabase/server";

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: (
    _name: string,
    _opts: unknown,
    fn: (span: { addEvent: () => void }) => unknown
  ) =>
    fn({
      addEvent: vi.fn(),
    }),
}));

const providerStub: AccommodationProviderAdapter = {
  checkAvailability: vi.fn(),
  createBooking: vi.fn(),
  getPropertyDetails: vi.fn(),
  name: "expedia",
  priceCheck: vi.fn(),
  searchAvailability: vi.fn(),
};

describe("AccommodationsService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (providerStub.searchAvailability as Mock).mockResolvedValue({
      ok: true,
      retries: 0,
      value: { properties: [] },
    });
  });

  test("returns empty results when RAG yields no property IDs", async () => {
    const supabaseClient = {
      rpc: vi.fn(async () => ({ data: [] })),
    } as unknown as TypedServerSupabase;

    const service = new AccommodationsService({
      cacheTtlSeconds: 300,
      provider: providerStub,
      supabase: async () => supabaseClient,
    });

    const result = await service.search(
      {
        checkin: "2025-01-01",
        checkout: "2025-01-02",
        guests: 2,
        location: "NYC",
      },
      { sessionId: "s1" }
    );

    const parsed = ACCOMMODATION_SEARCH_OUTPUT_SCHEMA.safeParse(result);
    expect(parsed.success).toBe(true);
    expect((providerStub.searchAvailability as Mock).mock.calls.length).toBe(1);
  });

  test("falls back to provider search when semanticQuery is absent", async () => {
    (providerStub.searchAvailability as Mock).mockResolvedValueOnce({
      ok: true,
      retries: 0,
      value: { properties: [] },
    });
    const supabaseClient = {
      rpc: vi.fn(async () => ({ data: undefined })),
    } as unknown as TypedServerSupabase;

    const service = new AccommodationsService({
      cacheTtlSeconds: 300,
      provider: providerStub,
      supabase: async () => supabaseClient,
    });

    await service.search(
      {
        checkin: "2025-01-01",
        checkout: "2025-01-02",
        guests: 2,
        location: "Seattle",
      },
      { sessionId: "s1" }
    );

    expect((providerStub.searchAvailability as Mock).mock.calls.length).toBe(1);
  });
});
