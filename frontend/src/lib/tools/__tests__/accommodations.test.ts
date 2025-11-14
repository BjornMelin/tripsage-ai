import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import {
  ACCOMMODATION_BOOKING_OUTPUT_SCHEMA,
  ACCOMMODATION_DETAILS_OUTPUT_SCHEMA,
  ACCOMMODATION_SEARCH_OUTPUT_SCHEMA,
} from "@/lib/schemas/accommodations";
import { createMockRedis } from "@/test/tool-helpers";

type SupabaseOverrides = {
  userId?: string | null;
};

const supabaseState = vi.hoisted(() => ({
  instance: createSupabaseStub(),
}));

const expediaState = vi.hoisted(() => ({
  checkAvailability: vi.fn(),
  getPropertyDetails: vi.fn(),
  search: vi.fn(),
}));

const secureUuidMock = vi.hoisted(() => vi.fn(() => "uuid-123"));

function createSupabaseStub(overrides: SupabaseOverrides = {}) {
  const sessionUser = overrides.userId === undefined ? "user-123" : overrides.userId;
  const baseQuery = {
    eq: vi.fn().mockReturnThis(),
    limit: vi.fn().mockReturnThis(),
    order: vi.fn().mockReturnThis(),
    select: vi.fn().mockReturnThis(),
  };
  return {
    auth: {
      getUser: vi.fn(async () => ({
        data: { user: sessionUser ? { id: sessionUser } : null },
      })),
    },
    from: vi.fn((table: string) => {
      if (table === "bookings") {
        return {
          insert: vi.fn(async () => ({ error: null })),
        };
      }
      if (table === "trips") {
        return {
          select: vi.fn(() => ({
            eq: vi.fn(() => ({
              limit: vi.fn(async () => ({ error: null })),
            })),
          })),
        };
      }
      return baseQuery;
    }),
    rpc: vi.fn(async () => ({ data: [], error: null })),
  };
}

function resetSupabase(overrides: SupabaseOverrides = {}) {
  supabaseState.instance = createSupabaseStub(overrides);
}

function resetExpedia() {
  expediaState.search.mockReset();
  expediaState.getPropertyDetails.mockReset();
  expediaState.checkAvailability.mockReset();
}

vi.mock("@/lib/supabase", () => ({
  createServerSupabase: vi.fn(async () => supabaseState.instance),
}));

vi.mock("@/lib/travel-api/expedia-client", () => {
  class ExpediaApiError extends Error {
    statusCode: number;
    constructor(statusCode: number) {
      super("Expedia error");
      this.statusCode = statusCode;
    }
  }
  return {
    ExpediaApiError,
    getExpediaClient: () => expediaState,
  };
});

vi.mock("@/lib/security/random", () => ({
  secureUuid: secureUuidMock,
}));

vi.mock("@/lib/payments/booking-payment", () => ({
  processBookingPayment: vi.fn(async () => ({
    bookingId: "payment-booking-id",
    confirmationNumber: "CN-12345",
    paymentIntentId: "pi_123",
  })),
}));

vi.mock("@upstash/ratelimit", () => ({
  Ratelimit: class {
    static slidingWindow() {
      return {};
    }
    limit = vi.fn(async () => ({ success: true }));
  },
}));

vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(),
}));

vi.mock("@/lib/mcp/client", () => ({
  createMcpClientHelper: vi.fn(),
  getMcpTool: vi.fn(),
}));

vi.mock("@/lib/tools/approvals", () => ({
  requireApproval: vi.fn(async () => {
    // Mock function returns undefined
  }),
}));

vi.mock("@/lib/env/server", () => ({
  getServerEnvVarWithFallback: vi.fn((key: string) => {
    if (key === "AIRBNB_MCP_URL") return process.env.AIRBNB_MCP_URL;
    if (key === "AIRBNB_MCP_API_KEY") return process.env.AIRBNB_MCP_API_KEY;
    if (key === "ACCOM_SEARCH_URL")
      return process.env.ACCOM_SEARCH_URL || "https://api.example.com";
    if (key === "ACCOM_SEARCH_TOKEN")
      return process.env.ACCOM_SEARCH_TOKEN || "test_token";
    return undefined;
  }),
}));

vi.mock("@/lib/cache/keys", () => ({
  canonicalizeParamsForCache: vi.fn((_params: unknown, prefix: string) => {
    return `${prefix}:test`;
  }),
}));

beforeEach(async () => {
  resetSupabase();
  resetExpedia();
  secureUuidMock.mockReset();
  secureUuidMock.mockReturnValue("uuid-123");
  vi.stubGlobal("fetch", vi.fn());
  const mod = await import("@/lib/env/server");
  (mod.getServerEnvVarWithFallback as ReturnType<typeof vi.fn>).mockImplementation(
    (key: string) => {
      if (key === "ACCOM_SEARCH_URL") return "https://api.example.com";
      if (key === "ACCOM_SEARCH_TOKEN") return "test_token";
      if (key === "AIRBNB_MCP_URL") return undefined;
      if (key === "AIRBNB_MCP_API_KEY") return undefined;
      if (key === "NEXT_PUBLIC_SUPABASE_URL") return "";
      if (key === "NEXT_PUBLIC_SUPABASE_ANON_KEY") return "";
      return undefined;
    }
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

const mockContext = {
  messages: [],
  toolCallId: "test-call-id",
};

describe("searchAccommodations", () => {
  test("validates inputs and returns structured output", async () => {
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(null);
    expediaState.search.mockResolvedValue({
      properties: [
        {
          id: "prop-1",
          name: "Hotel Paris",
          rates: [{ price: { total: "$120.00" } }],
          source: "hotel",
        },
      ],
      totalResults: 1,
    });
    const { searchAccommodations } = await import("@/lib/tools/accommodations");

    const result = await searchAccommodations.execute?.(
      {
        checkin: "2024-01-01",
        checkout: "2024-01-05",
        guests: 1,
        location: "Paris",
      },
      mockContext
    );

    const validated = ACCOMMODATION_SEARCH_OUTPUT_SCHEMA.parse(result);
    expect(validated.status).toBe("success");
    expect(validated.fromCache).toBe(false);
    expect(validated.provider).toBe("expedia");
    expect(validated.resultsReturned).toBe(1);
    expect(validated.totalResults).toBe(1);
    expect(validated.searchParameters).toMatchObject({
      checkin: "2024-01-01",
      checkout: "2024-01-05",
      guests: 1,
      location: "Paris",
    });
    expect(expediaState.search).toHaveBeenCalledWith(
      expect.objectContaining({
        guests: 1,
        location: "Paris",
      })
    );
  });

  test("returns cached result with normalized output", async () => {
    const { getRedis } = await import("@/lib/redis");
    const mockRedis = createMockRedis();
    await mockRedis.set("accom_search:test", {
      avgPrice: 100,
      fromCache: false,
      listings: [{ id: "1" }],
      maxPrice: 200,
      minPrice: 50,
      provider: "http_post",
      resultsReturned: 1,
      searchId: "cached-id",
      searchParameters: {},
      status: "success",
      tookMs: 100,
      totalResults: 1,
    });
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(mockRedis);
    const { searchAccommodations } = await import("@/lib/tools/accommodations");

    const result = await searchAccommodations.execute?.(
      {
        checkin: "2024-01-01",
        checkout: "2024-01-05",
        fresh: false,
        guests: 1,
        location: "Paris",
      },
      mockContext
    );

    const validated = ACCOMMODATION_SEARCH_OUTPUT_SCHEMA.parse(result);
    expect(validated.fromCache).toBe(true);
    expect(validated.searchId).toBe("cached-id");
    expect(expediaState.search).not.toHaveBeenCalled();
  });
});

describe("getAccommodationDetails", () => {
  test("validates inputs and returns structured output via HTTP", async () => {
    expediaState.getPropertyDetails.mockResolvedValue({
      id: "1",
      name: "Hotel",
      price: 100,
    });
    const { getAccommodationDetails } = await import("@/lib/tools/accommodations");

    const result = await getAccommodationDetails.execute?.(
      { listingId: "123" },
      mockContext
    );

    const validated = ACCOMMODATION_DETAILS_OUTPUT_SCHEMA.parse(result);
    expect(validated.status).toBe("success");
    expect(validated.provider).toBe("expedia");
    expect(validated.listing).toMatchObject({ id: "1", name: "Hotel" });
    expect(Object.keys(validated).sort()).toEqual(["listing", "provider", "status"]);
    expect(expediaState.getPropertyDetails).toHaveBeenCalledWith(
      expect.objectContaining({ propertyId: "123" })
    );
  });
});

describe("bookAccommodation", () => {
  test("validates inputs and returns structured output", async () => {
    const { requireApproval } = await import("@/lib/tools/approvals");
    (requireApproval as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      undefined
    );
    const { bookAccommodation } = await import("@/lib/tools/accommodations");

    const result = await bookAccommodation.execute?.(
      {
        bookingToken: "test-booking-token-123",
        checkin: "2024-01-01",
        checkout: "2024-01-05",
        guestEmail: "test@example.com",
        guestName: "Test User",
        guests: 1,
        listingId: "123",
        paymentMethodId: "pm_test_123",
        sessionId: "session-123",
      },
      mockContext
    );

    const validated = ACCOMMODATION_BOOKING_OUTPUT_SCHEMA.parse(result);
    expect(validated.status).toBe("success");
    expect(validated.bookingStatus).toBe("confirmed");
    expect(typeof validated.bookingId).toBe("string");
    expect(typeof validated.reference).toBe("string");
    expect(typeof validated.idempotencyKey).toBe("string");
    expect(validated.guestEmail).toBe("test@example.com");
    expect(validated.guestName).toBe("Test User");
    expect(Object.keys(validated).sort()).toEqual([
      "bookingId",
      "bookingStatus",
      "checkin",
      "checkout",
      "epsBookingId",
      "guestEmail",
      "guestName",
      "guestPhone",
      "guests",
      "holdOnly",
      "idempotencyKey",
      "listingId",
      "message",
      "paymentMethod",
      "reference",
      "specialRequests",
      "status",
      "stripePaymentIntentId",
      "tripId",
    ]);
  });

  test("throws when sessionId is missing", async () => {
    const { bookAccommodation } = await import("@/lib/tools/accommodations");

    await expect(
      bookAccommodation.execute?.(
        {
          bookingToken: "test-booking-token-123",
          checkin: "2024-01-01",
          checkout: "2024-01-05",
          guestEmail: "test@example.com",
          guestName: "Test User",
          guests: 1,
          listingId: "123",
          paymentMethodId: "pm_test_123",
        },
        mockContext
      )
    ).rejects.toThrow(/accom_booking_session_required/);
  });
});
