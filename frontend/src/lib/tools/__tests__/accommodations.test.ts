import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import {
  ACCOMMODATION_BOOKING_OUTPUT_SCHEMA,
  ACCOMMODATION_DETAILS_OUTPUT_SCHEMA,
  ACCOMMODATION_SEARCH_OUTPUT_SCHEMA,
} from "@/lib/schemas/accommodations";
import {
  createMockHttpResponse,
  createMockMcpTool,
  createMockRedis,
} from "@/test/tool-helpers";

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
  vi.stubGlobal("fetch", vi.fn());
  const mod = await import("@/lib/env/server");
  (mod.getServerEnvVarWithFallback as ReturnType<typeof vi.fn>).mockImplementation(
    (key: string) => {
      if (key === "ACCOM_SEARCH_URL") return "https://api.example.com";
      if (key === "ACCOM_SEARCH_TOKEN") return "test_token";
      if (key === "AIRBNB_MCP_URL") return undefined;
      if (key === "AIRBNB_MCP_API_KEY") return undefined;
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
    const { searchAccommodations } = await import("@/lib/tools/accommodations");
    const mockData = {
      listings: [{ id: "1", name: "Hotel" }],
      total_results: 1,
    };
    const mockRes = createMockHttpResponse(mockData);
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);

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
    expect(typeof validated.tookMs).toBe("number");
    expect(Array.isArray(validated.listings)).toBe(true);
    expect(typeof validated.provider).toBe("string");
    expect(typeof validated.searchId).toBe("string");
    expect(Object.keys(validated).sort()).toEqual([
      "avgPrice",
      "fromCache",
      "listings",
      "maxPrice",
      "minPrice",
      "provider",
      "resultsReturned",
      "searchId",
      "searchParameters",
      "status",
      "tookMs",
      "totalResults",
    ]);
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
  });
});

describe("getAccommodationDetails", () => {
  test("validates inputs and returns structured output via HTTP", async () => {
    const { getAccommodationDetails } = await import("@/lib/tools/accommodations");
    const mockData = { id: "1", name: "Hotel", price: 100 };
    const mockRes = createMockHttpResponse(mockData);
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);

    const result = await getAccommodationDetails.execute?.(
      { listingId: "123" },
      mockContext
    );

    const validated = ACCOMMODATION_DETAILS_OUTPUT_SCHEMA.parse(result);
    expect(validated.status).toBe("success");
    expect(validated.provider).toBe("http_get");
    expect(validated.listing).toEqual(mockData);
    expect(Object.keys(validated).sort()).toEqual(["listing", "provider", "status"]);
  });

  test("returns structured output via MCP when available", async () => {
    const { createMcpClientHelper, getMcpTool } = await import("@/lib/mcp/client");
    const mockClient = {
      close: vi.fn(async () => {
        // Mock function returns undefined
      }),
    };
    const mockTool = createMockMcpTool({ id: "1", name: "Hotel" });
    (createMcpClientHelper as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockClient
    );
    (getMcpTool as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockTool);
    const { getServerEnvVarWithFallback } = await import("@/lib/env/server");
    (getServerEnvVarWithFallback as ReturnType<typeof vi.fn>).mockImplementation(
      (key: string) => {
        if (key === "AIRBNB_MCP_URL") return "https://mcp.example.com";
        if (key === "AIRBNB_MCP_API_KEY") return "mcp_key";
        return undefined;
      }
    );
    const { getAccommodationDetails } = await import("@/lib/tools/accommodations");

    const result = await getAccommodationDetails.execute?.(
      { listingId: "123" },
      mockContext
    );

    const validated = ACCOMMODATION_DETAILS_OUTPUT_SCHEMA.parse(result);
    expect(validated.status).toBe("success");
    expect(validated.provider).toBe("mcp_sse");
    expect(Object.keys(validated).sort()).toEqual(["listing", "provider", "status"]);
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
    expect(validated.bookingStatus).toBe("pending_confirmation");
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
