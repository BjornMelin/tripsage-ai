/** @vitest-environment jsdom */

import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { type ModernHotelResult, ModernHotelResults } from "../modern-hotel-results";

const BASE_HOTEL: ModernHotelResult = {
  ai: {
    personalizedTags: ["hybrid-amadeus"],
    reason: "Test reason",
    recommendation: 9,
  },
  allInclusive: { available: false, inclusions: [], tier: "basic" },
  amenities: { essential: ["wifi", "gym"], premium: [], unique: [] },
  availability: { flexible: true, roomsLeft: 2, urgency: "medium" },
  category: "hotel",
  guestExperience: { highlights: [], recentMentions: [], vibe: "business" },
  id: "hotel-1",
  images: { count: 1, gallery: [], main: "https://example.com/photo.jpg" },
  location: { address: "123 St", city: "Paris", district: "1st", landmarks: [] },
  name: "Test Hotel",
  pricing: {
    basePrice: 150,
    currency: "USD",
    priceHistory: "stable",
    pricePerNight: 150,
    taxes: 0,
    totalPrice: 300,
  },
  reviewCount: 120,
  starRating: 4,
  sustainability: { certified: false, practices: [], score: 0 },
  userRating: 4.6,
};

describe("ModernHotelResults", () => {
  it("renders hotel cards and keeps actions enabled", () => {
    const onSelect = vi.fn().mockResolvedValue(undefined);
    const onSave = vi.fn();

    render(
      <ModernHotelResults
        results={[BASE_HOTEL]}
        loading={false}
        onSelect={onSelect}
        onSaveToWishlist={onSave}
      />
    );

    expect(screen.getByText("Test Hotel")).toBeInTheDocument();
    expect(screen.getByText("4.6")).toBeInTheDocument();
    expect(screen.getByText(/AI Pick/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /View Details/i })).toBeEnabled();
    expect(onSelect).not.toHaveBeenCalled();
  });
});
