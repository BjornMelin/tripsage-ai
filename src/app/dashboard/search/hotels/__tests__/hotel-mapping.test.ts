/** @vitest-environment node */

import type { Accommodation } from "@schemas/search";
import { describe, expect, it } from "vitest";
import { FALLBACK_HOTEL_IMAGE } from "@/lib/constants/images";
import { unsafeCast } from "@/test/helpers/unsafe-cast";
import { mapAccommodationToHotelResult } from "../hotel-mapping";

function buildBaseAccommodation(overrides: Partial<Accommodation> = {}): Accommodation {
  return {
    amenities: ["wifi"],
    checkIn: "2025-01-01T00:00:00Z",
    checkOut: "2025-01-02T00:00:00Z",
    id: "acc-1",
    location: "Paris",
    name: "Example Hotel",
    pricePerNight: 120,
    rating: 4.2,
    totalPrice: 240,
    type: "hotel",
    ...overrides,
  };
}

describe("mapAccommodationToHotelResult", () => {
  it("maps a minimal accommodation with stable defaults", () => {
    const result = mapAccommodationToHotelResult(buildBaseAccommodation());
    expect(result.category).toBe("hotel");
    expect(result.images.main).toBe(FALLBACK_HOTEL_IMAGE);
    expect(result.images.gallery).toEqual([]);
    expect(result.pricing.currency).toBe("USD");
    expect(result.pricing.taxesEstimated).toBe(true);
    expect(result.availability.urgency).toBe("medium");
  });

  it("passes through valid star ratings (1-5)", () => {
    for (const value of [1, 2, 3, 4, 5] as const) {
      const result = mapAccommodationToHotelResult(
        buildBaseAccommodation({ starRating: value })
      );
      expect(result.starRating).toBe(value);
    }
  });

  it("falls back to accommodation id when name is empty or whitespace", () => {
    const emptyName = mapAccommodationToHotelResult(
      buildBaseAccommodation({ id: "acc-empty", name: "" })
    );
    expect(emptyName.name).toBe("acc-empty");

    const whitespaceName = mapAccommodationToHotelResult(
      buildBaseAccommodation({ id: "acc-space", name: "   " })
    );
    expect(whitespaceName.name).toBe("acc-space");
  });

  it("normalizes invalid star ratings to undefined", () => {
    expect(
      mapAccommodationToHotelResult(buildBaseAccommodation({ starRating: 0 }))
        .starRating
    ).toBeUndefined();
    expect(
      mapAccommodationToHotelResult(buildBaseAccommodation({ starRating: -1 }))
        .starRating
    ).toBeUndefined();
    expect(
      mapAccommodationToHotelResult(buildBaseAccommodation({ starRating: 6 }))
        .starRating
    ).toBeUndefined();
  });

  it("derives a luxury vibe for resorts", () => {
    const result = mapAccommodationToHotelResult(
      buildBaseAccommodation({ category: "resort" })
    );
    expect(result.guestExperience.vibe).toBe("luxury");
  });

  it("falls back to hotel category for unknown categories", () => {
    const result = mapAccommodationToHotelResult(
      buildBaseAccommodation({
        category: unsafeCast<Accommodation["category"]>("castle"),
      })
    );
    expect(result.category).toBe("hotel");
  });

  it("converts rating into a 1-10 recommendation score", () => {
    const result = mapAccommodationToHotelResult(
      buildBaseAccommodation({ rating: 4.8 })
    );
    expect(result.ai.recommendation).toBe(10);
  });

  it("clamps recommendation score for out-of-range ratings", () => {
    expect(
      mapAccommodationToHotelResult(buildBaseAccommodation({ rating: -2 })).ai
        .recommendation
    ).toBe(1);
    expect(
      mapAccommodationToHotelResult(buildBaseAccommodation({ rating: 99 })).ai
        .recommendation
    ).toBe(10);
  });

  it("uses provided images for main and gallery", () => {
    const result = mapAccommodationToHotelResult(
      buildBaseAccommodation({ images: ["img-1", "img-2"] })
    );
    expect(result.images.count).toBe(2);
    expect(result.images.main).toBe("img-1");
    expect(result.images.gallery).toEqual(["img-1", "img-2"]);
  });

  it("prefers district from address when provided", () => {
    const result = mapAccommodationToHotelResult(
      buildBaseAccommodation({
        address: unsafeCast<Accommodation["address"]>({
          cityName: "Paris",
          district: "Center",
          lines: ["123 Rue Example"],
        }),
      })
    );
    expect(result.location.district).toBe("Center");
  });
});
