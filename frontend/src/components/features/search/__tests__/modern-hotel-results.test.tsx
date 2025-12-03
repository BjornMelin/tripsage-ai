/** @vitest-environment jsdom */

import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { render } from "@/test/test-utils";
import { type ModernHotelResult, ModernHotelResults } from "../modern-hotel-results";

const BaseHotel: ModernHotelResult = {
  ai: { personalizedTags: [], reason: "Great value", recommendation: 8 },
  amenities: { essential: ["wifi", "pool"], premium: [], unique: [] },
  availability: { flexible: true, roomsLeft: 5, urgency: "low" },
  category: "hotel",
  guestExperience: { highlights: [], recentMentions: [], vibe: "business" },
  id: "h1",
  images: { count: 0, gallery: [], main: "" },
  location: {
    address: "123 Main St",
    city: "City",
    district: "Center",
    landmarks: [],
  },
  name: "Test Hotel",
  pricing: {
    basePrice: 200,
    currency: "USD",
    priceHistory: "stable",
    pricePerNight: 200,
    taxes: 0,
    totalPrice: 400,
  },
  reviewCount: 120,
  starRating: 4,
  sustainability: { certified: false, practices: [], score: 0 },
  userRating: 4.5,
};

describe("ModernHotelResults", () => {
  it("invokes onSelect when View Details is clicked", () => {
    const onSelect = vi.fn().mockResolvedValue(undefined);
    render(
      <ModernHotelResults
        results={[BaseHotel]}
        onSelect={onSelect}
        onSaveToWishlist={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /view details/i }));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: "h1" }));
  });

  it("toggles wishlist state", () => {
    const onSave = vi.fn();
    render(
      <ModernHotelResults
        results={[BaseHotel]}
        onSelect={vi.fn()}
        onSaveToWishlist={onSave}
      />
    );

    const wishlistButton = screen.getByRole("button", { name: /wishlist/i });
    fireEvent.click(wishlistButton);
    expect(onSave).toHaveBeenCalledWith("h1");
  });
});
