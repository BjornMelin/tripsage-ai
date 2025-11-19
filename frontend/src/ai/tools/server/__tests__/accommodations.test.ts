import {
  bookAccommodation,
  checkAvailability,
  getAccommodationDetails,
  searchAccommodations,
} from "@ai/tools/server/accommodations";
import {
  ACCOMMODATION_BOOKING_OUTPUT_SCHEMA,
  ACCOMMODATION_CHECK_AVAILABILITY_OUTPUT_SCHEMA,
  ACCOMMODATION_DETAILS_OUTPUT_SCHEMA,
  ACCOMMODATION_SEARCH_OUTPUT_SCHEMA,
  type AccommodationBookingRequest,
  type AccommodationCheckAvailabilityParams,
} from "@schemas/accommodations";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const headersState = vi.hoisted(() => ({
  userId: "user-123" as string | null,
}));

vi.mock("next/headers", () => ({
  headers: vi.fn(() => ({
    get: (key: string) => {
      if (key === "x-user-id") {
        return headersState.userId ?? null;
      }
      return null;
    },
  })),
}));

const supabaseState = vi.hoisted(() => ({
  instance: createSupabaseStub(),
}));

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => supabaseState.instance),
}));

const expediaState = vi.hoisted(() => ({
  checkAvailability: vi.fn(),
  getPropertyDetails: vi.fn(),
  searchAvailability: vi.fn(),
}));

const secureUuidMock = vi.hoisted(() => vi.fn(() => "uuid-123"));

vi.mock("@/lib/travel-api/expedia-client", () => {
  class ExpediaApiError extends Error {
    code: string;
    statusCode?: number;
    constructor(message: string, code: string, statusCode?: number) {
      super(message);
      this.code = code;
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
    confirmationNumber: "CN-12345",
    itineraryId: "itinerary-1",
    paymentIntentId: "pi_123",
  })),
}));

vi.mock("@ai/tools/server/approvals", () => ({
  requireApproval: vi.fn(async () => undefined),
}));

vi.mock("@/lib/telemetry/span", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/telemetry/span")>(
      "@/lib/telemetry/span"
    );
  return {
    ...actual,
    withTelemetrySpan: vi.fn((_name: string, _options: unknown, fn: () => unknown) =>
      fn()
    ),
  };
});

function createSupabaseStub() {
  return {
    from: vi.fn(() => ({
      insert: vi.fn(() => ({
        select: vi.fn(() => ({
          single: vi.fn(async () => ({ data: { id: "booking-1" }, error: null })),
        })),
      })),
    })),
  };
}

describe("accommodations tools", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    headersState.userId = "user-123";
    supabaseState.instance = createSupabaseStub();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  test("searchAccommodations returns normalized results", async () => {
    const mockResponse = {
      properties: [
        {
          address: "123 Main St",
          amenities: ["wifi"],
          name: "Test Hotel",
          property_id: "prop-1",
          rooms: [],
          score: 0.9,
          star_rating: 4,
          status: "AVAILABLE",
          summary: {
            location: { address: "123 Main St", coordinates: { lat: 1, lon: 2 } },
            name: "Test Hotel",
            star_rating: { value: 4 },
          },
        },
      ],
    };

    expediaState.searchAvailability.mockResolvedValueOnce(
      mockResponse as unknown as Record<string, unknown>
    );

    const result = await searchAccommodations.execute?.(
      {
        checkin: "2025-01-01",
        checkout: "2025-01-05",
        guests: 2,
        location: "NYC",
      },
      {
        messages: [],
        toolCallId: "test-call-id",
      }
    );

    const parsed = ACCOMMODATION_SEARCH_OUTPUT_SCHEMA.safeParse(result);
    expect(parsed.success).toBe(true);
  });

  test("checkAvailability returns parsed result", async () => {
    const mockAvailability = {
      bookingToken: "token-123",
      expiresAt: "2025-01-01T00:00:00Z",
      price: { amount: 100, currency: "USD" },
      propertyId: "prop-1",
      rateId: "rate-1",
      status: "AVAILABLE",
    };
    expediaState.checkAvailability.mockResolvedValueOnce(
      mockAvailability as unknown as Record<string, unknown>
    );

    const result = await checkAvailability.execute?.(
      {
        priceCheckToken: "token-123",
        propertyId: "prop-1",
        rateId: "rate-1",
        roomId: "room-1",
      } as AccommodationCheckAvailabilityParams,
      {
        messages: [],
        toolCallId: "test-call-id",
      }
    );

    const parsed = ACCOMMODATION_CHECK_AVAILABILITY_OUTPUT_SCHEMA.safeParse(result);
    expect(parsed.success).toBe(true);
  });

  test("getAccommodationDetails returns parsed result", async () => {
    expediaState.getPropertyDetails.mockResolvedValueOnce({
      id: "prop-1",
      name: "Test Hotel",
    } as unknown as Record<string, unknown>);

    const result = await getAccommodationDetails.execute?.(
      { listingId: "prop-1" },
      {
        messages: [],
        toolCallId: "test-call-id",
      }
    );

    const parsed = ACCOMMODATION_DETAILS_OUTPUT_SCHEMA.safeParse(result);
    expect(parsed.success).toBe(true);
  });

  test("bookAccommodation returns parsed result", async () => {
    expediaState.checkAvailability.mockResolvedValueOnce({
      bookingToken: "token-123",
      expiresAt: "2025-01-01T00:00:00Z",
      price: { amount: 100, currency: "USD" },
      propertyId: "prop-1",
      rateId: "rate-1",
      status: "AVAILABLE",
    } as unknown as Record<string, unknown>);

    const payload: AccommodationBookingRequest = {
      amount: 100,
      bookingToken: "token-123",
      checkin: "2025-01-01",
      checkout: "2025-01-05",
      currency: "USD",
      guestEmail: "test@example.com",
      guestName: "Test User",
      guestPhone: "+15551234567",
      guests: 2,
      listingId: "prop-1",
      paymentMethodId: "pm_123",
      sessionId: "session-1",
      tripId: "trip-1",
    };

    const result = await bookAccommodation.execute?.(payload, {
      messages: [],
      toolCallId: "test-call-id",
    });

    const parsed = ACCOMMODATION_BOOKING_OUTPUT_SCHEMA.safeParse(result);
    expect(parsed.success).toBe(true);
  });
});
