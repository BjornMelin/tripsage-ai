import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(),
}));

vi.mock("@/lib/security/random", () => ({
  secureUuid: vi.fn(() => "test-uuid-123"),
}));

vi.mock("@ai-sdk/mcp", () => ({
  // biome-ignore lint/style/useNamingConvention: Library export name
  experimental_createMCPClient: vi.fn(),
}));

const env = process.env;

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
  process.env = {
    ...env,
    ACCOM_SEARCH_TOKEN: "test_token",
    ACCOM_SEARCH_URL: "https://api.example.com/search",
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
  test("validates checkout > checkin", async () => {
    const { searchAccommodations } = await import("../accommodations");
    await expect(
      searchAccommodations.execute?.(
        {
          checkin: "2025-07-05",
          checkout: "2025-07-01",
          guests: 2,
          location: "Paris",
        },
        mockContext
      )
    ).rejects.toThrow(/checkout must be after checkin/);
  });

  test("validates priceMax >= priceMin", async () => {
    const { searchAccommodations } = await import("../accommodations");
    await expect(
      searchAccommodations.execute?.(
        {
          checkin: "2025-07-01",
          checkout: "2025-07-05",
          guests: 2,
          location: "Paris",
          priceMax: 50,
          priceMin: 100,
        },
        mockContext
      )
    ).rejects.toThrow(/priceMax must be >= priceMin/);
  });

  test("uses HTTP POST fallback with all filters", async () => {
    const mockRes = {
      json: async () => ({ listings: [], total_results: 0 }),
      ok: true,
    } as Response;
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(null);

    const { searchAccommodations } = await import("../accommodations");
    await searchAccommodations.execute?.(
      {
        adults: 2,
        amenities: ["wifi", "pool"],
        checkin: "2025-07-01",
        checkout: "2025-07-05",
        children: 1,
        freeCancellation: true,
        guests: 2,
        instantBook: true,
        location: "Paris",
        priceMax: 100,
        priceMin: 50,
        propertyTypes: ["hotel", "apartment"],
      },
      mockContext
    );

    const call = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[1]?.method).toBe("POST");
    const body = JSON.parse(call[1]?.body as string);
    expect(body.min_price).toBe(50);
    expect(body.max_price).toBe(100);
    expect(body.property_types).toEqual(["hotel", "apartment"]);
    expect(body.amenities).toEqual(["wifi", "pool"]);
    expect(body.instant_book).toBe(true);
    expect(body.free_cancellation).toBe(true);
    expect(body.adults).toBe(2);
    expect(body.children).toBe(1);
  });

  test("returns cached result when available", async () => {
    const mockRedis = {
      get: vi.fn().mockResolvedValue({
        fromCache: false,
        listings: [{ id: "cached-1" }],
        provider: "cache",
        status: "success",
      }),
      set: vi.fn(),
    };
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(mockRedis);

    const { searchAccommodations } = await import("../accommodations");
    const result = await searchAccommodations.execute?.(
      {
        checkin: "2025-07-01",
        checkout: "2025-07-05",
        fresh: false,
        guests: 2,
        location: "Paris",
      },
      mockContext
    );

    expect(result).toHaveProperty("fromCache", true);
    expect(mockRedis.get).toHaveBeenCalled();
    expect(fetch).not.toHaveBeenCalled();
  });

  test("caches result after successful search", async () => {
    const mockRes = {
      json: async () => ({ listings: [{ id: "1" }], total_results: 1 }),
      ok: true,
    } as Response;
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);
    const mockRedis = {
      get: vi.fn().mockResolvedValue(null),
      set: vi.fn(),
    };
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(mockRedis);

    const { searchAccommodations } = await import("../accommodations");
    await searchAccommodations.execute?.(
      {
        checkin: "2025-07-01",
        checkout: "2025-07-05",
        guests: 2,
        location: "Paris",
      },
      mockContext
    );

    expect(mockRedis.set).toHaveBeenCalled();
    const setCall = mockRedis.set.mock.calls[0];
    expect(setCall[2]).toEqual({ ex: 300 });
  });

  test("handles timeout with retries", async () => {
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(null);
    let callCount = 0;
    (fetch as unknown as ReturnType<typeof vi.fn>).mockImplementation(() => {
      callCount++;
      const error = new Error("AbortError");
      error.name = "AbortError";
      return Promise.reject(error);
    });

    const { searchAccommodations } = await import("../accommodations");
    await expect(
      searchAccommodations.execute?.(
        {
          checkin: "2025-07-01",
          checkout: "2025-07-05",
          guests: 2,
          location: "Paris",
        },
        mockContext
      )
    ).rejects.toThrow(/accom_search_timeout/);
    // Should have retried 3 times (initial + 2 retries)
    expect(callCount).toBeGreaterThanOrEqual(3);
  });

  test("maps HTTP errors to error codes", async () => {
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(null);

    const testCases = [
      { expectedCode: "accom_search_rate_limited", status: 429 },
      { expectedCode: "accom_search_unauthorized", status: 401 },
      { expectedCode: "accom_search_payment_required", status: 402 },
      { expectedCode: "accom_search_failed", status: 500 },
    ];

    for (const { status, expectedCode } of testCases) {
      const mockRes = {
        ok: false,
        status,
        text: async () => "error",
      } as Response;
      (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);

      const { searchAccommodations } = await import("../accommodations");
      await expect(
        searchAccommodations.execute?.(
          {
            checkin: "2025-07-01",
            checkout: "2025-07-05",
            guests: 2,
            location: "Paris",
          },
          mockContext
        )
      ).rejects.toThrow(new RegExp(expectedCode));
    }
  });

  test("throws when not configured", async () => {
    process.env.ACCOM_SEARCH_URL = "";
    process.env.AIRBNB_MCP_URL = "";
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(null);

    const { searchAccommodations } = await import("../accommodations");
    await expect(
      searchAccommodations.execute?.(
        {
          checkin: "2025-07-01",
          checkout: "2025-07-05",
          guests: 2,
          location: "Paris",
        },
        mockContext
      )
    ).rejects.toThrow(/accom_search_not_configured/);
  });
});

describe("bookAccommodation", () => {
  test("validates checkout > checkin", async () => {
    const { bookAccommodation } = await import("../accommodations");
    await expect(
      bookAccommodation.execute?.(
        {
          checkin: "2025-07-05",
          checkout: "2025-07-01",
          guestEmail: "john@example.com",
          guestName: "John Doe",
          guests: 2,
          listingId: "listing-123",
          sessionId: "session-456",
        },
        mockContext
      )
    ).rejects.toThrow(/checkout must be after checkin/);
  });

  test("requires approval and throws with metadata", async () => {
    const mockRedis = {
      get: vi.fn().mockResolvedValue("pending"),
      set: vi.fn(),
    };
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(mockRedis);

    const { bookAccommodation } = await import("../accommodations");
    await expect(
      bookAccommodation.execute?.(
        {
          checkin: "2025-07-01",
          checkout: "2025-07-05",
          guestEmail: "john@example.com",
          guestName: "John Doe",
          guests: 2,
          listingId: "listing-123",
          sessionId: "session-456",
        },
        mockContext
      )
    ).rejects.toThrow(/approval_required/);
  });

  test("generates idempotency key if not provided", async () => {
    const mockRedis = {
      get: vi.fn().mockResolvedValue("yes"),
      set: vi.fn(),
    };
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(mockRedis);

    const { bookAccommodation } = await import("../accommodations");
    const result = await bookAccommodation.execute?.(
      {
        checkin: "2025-07-01",
        checkout: "2025-07-05",
        guestEmail: "john@example.com",
        guestName: "John Doe",
        guests: 2,
        listingId: "listing-123",
        sessionId: "session-456",
      },
      mockContext
    );

    expect(result).toHaveProperty("idempotencyKey", "test-uuid-123");
  });

  test("uses provided idempotency key", async () => {
    const mockRedis = {
      get: vi.fn().mockResolvedValue("yes"),
      set: vi.fn(),
    };
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(mockRedis);

    const { bookAccommodation } = await import("../accommodations");
    const result = await bookAccommodation.execute?.(
      {
        checkin: "2025-07-01",
        checkout: "2025-07-05",
        guestEmail: "john@example.com",
        guestName: "John Doe",
        guests: 2,
        idempotencyKey: "custom-key-123",
        listingId: "listing-123",
        sessionId: "session-456",
      },
      mockContext
    );

    expect(result).toHaveProperty("idempotencyKey", "custom-key-123");
  });

  test("returns booking with all fields", async () => {
    const mockRedis = {
      get: vi.fn().mockResolvedValue("yes"),
      set: vi.fn(),
    };
    const { getRedis } = await import("@/lib/redis");
    (getRedis as ReturnType<typeof vi.fn>).mockReturnValue(mockRedis);

    const { bookAccommodation } = await import("../accommodations");
    const result = await bookAccommodation.execute?.(
      {
        checkin: "2025-07-01",
        checkout: "2025-07-05",
        guestEmail: "john@example.com",
        guestName: "John Doe",
        guestPhone: "+1234567890",
        guests: 2,
        holdOnly: true,
        listingId: "listing-123",
        paymentMethod: "card-123",
        sessionId: "session-456",
        specialRequests: "Late check-in please",
        tripId: "trip-789",
      },
      mockContext
    );

    expect(result).toHaveProperty("status", "success");
    expect(result).toHaveProperty("bookingId");
    expect(result).toHaveProperty("listingId", "listing-123");
    expect(result).toHaveProperty("guestName", "John Doe");
    expect(result).toHaveProperty("guestEmail", "john@example.com");
    expect(result).toHaveProperty("guestPhone", "+1234567890");
    expect(result).toHaveProperty("holdOnly", true);
    expect(result).toHaveProperty("specialRequests", "Late check-in please");
    expect(result).toHaveProperty("tripId", "trip-789");
    expect(result).toHaveProperty("paymentMethod", "card-123");
    expect(result).toHaveProperty("bookingStatus", "hold_created");
  });
});

describe("getAccommodationDetails", () => {
  test("uses HTTP GET fallback", async () => {
    const mockRes = {
      json: async () => ({ id: "listing-123", name: "Test Listing" }),
      ok: true,
    } as Response;
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);

    const { getAccommodationDetails } = await import("../accommodations");
    const result = await getAccommodationDetails.execute?.(
      {
        adults: 2,
        checkin: "2025-07-01",
        checkout: "2025-07-05",
        children: 1,
        listingId: "listing-123",
      },
      mockContext
    );

    expect(result).toHaveProperty("status", "success");
    expect(result).toHaveProperty("listing");
    const call = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    const url = new URL(call[0] as string);
    expect(url.searchParams.get("listing_id")).toBe("listing-123");
    expect(url.searchParams.get("checkin")).toBe("2025-07-01");
    expect(url.searchParams.get("adults")).toBe("2");
  });

  test("maps HTTP errors to error codes", async () => {
    const testCases = [
      { expectedCode: "accom_details_not_found", status: 404 },
      { expectedCode: "accom_details_rate_limited", status: 429 },
      { expectedCode: "accom_details_unauthorized", status: 401 },
      { expectedCode: "accom_details_failed", status: 500 },
    ];

    for (const { status, expectedCode } of testCases) {
      const mockRes = {
        ok: false,
        status,
        text: async () => "error",
      } as Response;
      (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockRes);

      const { getAccommodationDetails } = await import("../accommodations");
      await expect(
        getAccommodationDetails.execute?.(
          {
            listingId: "listing-123",
          },
          mockContext
        )
      ).rejects.toThrow(new RegExp(expectedCode));
    }
  });
});
