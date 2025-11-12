import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import {
  createMockHttpResponse,
  createMockMcpTool,
  createMockRedis,
} from "@/test/tool-helpers";
import {
  ACCOMMODATION_BOOKING_OUTPUT_SCHEMA,
  ACCOMMODATION_DETAILS_OUTPUT_SCHEMA,
  ACCOMMODATION_SEARCH_OUTPUT_SCHEMA,
} from "@/types/accommodations";

vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(),
}));

vi.mock("@/lib/mcp/client", () => ({
  createMcpClientHelper: vi.fn(),
  getMcpTool: vi.fn(),
}));

vi.mock("@/lib/tools/approvals", () => ({
  requireApproval: vi.fn(async () => {}),
}));

vi.mock("@/lib/cache/keys", () => ({
  canonicalizeParamsForCache: vi.fn((_params: unknown, prefix: string) => {
    return `${prefix}:test`;
  }),
}));

const env = process.env;

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
  process.env = {
    ...env,
    ACCOM_SEARCH_TOKEN: "test_token",
    ACCOM_SEARCH_URL: "https://api.example.com",
  };
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
  process.env = env;
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
      close: vi.fn(async () => {}),
    };
    const mockTool = createMockMcpTool({ id: "1", name: "Hotel" });
    (createMcpClientHelper as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockClient
    );
    (getMcpTool as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockTool);
    process.env.AIRBNB_MCP_URL = "https://mcp.example.com";
    process.env.AIRBNB_MCP_API_KEY = "mcp_key";
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
        checkin: "2024-01-01",
        checkout: "2024-01-05",
        guestEmail: "test@example.com",
        guestName: "Test User",
        guests: 1,
        listingId: "123",
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
          checkin: "2024-01-01",
          checkout: "2024-01-05",
          guestEmail: "test@example.com",
          guestName: "Test User",
          guests: 1,
          listingId: "123",
        },
        mockContext
      )
    ).rejects.toThrow(/accom_booking_session_required/);
  });
});
