/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { makeJsonRequest, resetApiRouteMocks } from "@/test/helpers/api-route";
import { createRouteParamsContext } from "@/test/helpers/route";

const personalizeHotelsMock = vi.hoisted(() => vi.fn());

vi.mock("@ai/services/hotel-personalization", () => ({
  getDefaultPersonalization: vi.fn((hotel: { location: string; name: string }) => ({
    personalizedTags: [],
    reason: `${hotel.name} is a business option in ${hotel.location}.`,
    score: 6,
    vibe: "business",
  })),
  personalizeHotels: personalizeHotelsMock,
}));

const validPayload = {
  hotels: [
    {
      amenities: ["wifi"],
      category: "hotel",
      location: "Denver",
      name: "Union Station Hotel",
      pricePerNight: 180,
      rating: 4.2,
      starRating: 4,
    },
  ],
  preferences: {
    forBusiness: true,
    preferredAmenities: ["wifi"],
  },
};

describe("/api/accommodations/personalize route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetApiRouteMocks();
  });

  it("returns 400 validation errors before invoking personalization", async () => {
    const { POST } = await import("../route");
    const req = makeJsonRequest(
      "/api/accommodations/personalize",
      { hotels: [], preferences: {} },
      { method: "POST" }
    );

    const res = await POST(req, createRouteParamsContext());
    const body = (await res.json()) as { error: string; reason: string };

    expect(res.status).toBe(400);
    expect(body).toMatchObject({
      error: "invalid_request",
      reason: "Request validation failed",
    });
    expect(personalizeHotelsMock).not.toHaveBeenCalled();
  });

  it("returns 503 with deterministic fallback when personalization dependency fails", async () => {
    personalizeHotelsMock.mockRejectedValueOnce(new Error("provider unavailable"));

    const { POST } = await import("../route");
    const req = makeJsonRequest("/api/accommodations/personalize", validPayload, {
      method: "POST",
    });

    const res = await POST(req, createRouteParamsContext());
    const body = (await res.json()) as {
      fallback: boolean;
      results: Array<{ hotelName: string; score: number }>;
      warning: string;
    };

    expect(res.status).toBe(503);
    expect(body).toEqual({
      fallback: true,
      results: [
        expect.objectContaining({
          hotelName: "Union Station Hotel",
          score: 6,
        }),
      ],
      warning: "ai_service_unavailable",
    });
  });
});
