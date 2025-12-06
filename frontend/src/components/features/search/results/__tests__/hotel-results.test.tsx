/** @vitest-environment jsdom */

import type { HotelResult } from "@schemas/search";
import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { render } from "@/test/test-utils";
import { HotelResults } from "../hotel-results";

/** Factory for creating hotel fixtures with optional overrides. */
function CreateHotel(overrides: Partial<HotelResult> = {}): HotelResult {
  return {
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
      taxesEstimated: false,
      totalPrice: 400,
    },
    reviewCount: 120,
    starRating: 4,
    sustainability: { certified: false, practices: [], score: 0 },
    userRating: 4.5,
    ...overrides,
  };
}

const BaseHotel = CreateHotel();

describe("HotelResults", () => {
  it("invokes onSelect when View Details is clicked", () => {
    const onSelect = vi.fn().mockResolvedValue(undefined);
    render(
      <HotelResults
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
      <HotelResults
        results={[BaseHotel]}
        onSelect={vi.fn()}
        onSaveToWishlist={onSave}
      />
    );

    const wishlistButton = screen.getByRole("button", { name: /wishlist/i });
    fireEvent.click(wishlistButton);
    expect(onSave).toHaveBeenCalledWith("h1");
  });

  describe("distance sorting", () => {
    const searchCenter = { lat: 48.8566, lng: 2.3522 }; // Paris center

    const nearHotel = CreateHotel({
      id: "near",
      location: {
        address: "Near",
        city: "Paris",
        coordinates: { lat: 48.857, lng: 2.353 }, // ~100m from center
        district: "1st",
        landmarks: [],
      },
      name: "Near Hotel",
      pricing: { ...BaseHotel.pricing, totalPrice: 500 },
    });

    const farHotel = CreateHotel({
      id: "far",
      location: {
        address: "Far",
        city: "Versailles",
        coordinates: { lat: 48.8049, lng: 2.1204 }, // ~18km from center
        district: "Versailles",
        landmarks: [],
      },
      name: "Far Hotel",
      pricing: { ...BaseHotel.pricing, totalPrice: 200 },
    });

    const noCoordHotel = CreateHotel({
      id: "nocoord",
      location: {
        address: "Unknown",
        city: "Paris",
        district: "Unknown",
        landmarks: [],
        // No coordinates
      },
      name: "No Coord Hotel",
    });

    it("includes distance in sort cycle when searchCenter is provided", () => {
      render(
        <HotelResults
          results={[nearHotel, farHotel]}
          onSelect={vi.fn()}
          onSaveToWishlist={vi.fn()}
          searchCenter={searchCenter}
        />
      );

      const changeSortButton = screen.getByRole("button", { name: /change sort/i });

      // Default is AI, cycle through: ai -> price -> rating -> distance
      fireEvent.click(changeSortButton); // price
      fireEvent.click(changeSortButton); // rating
      fireEvent.click(changeSortButton); // distance

      // Verify sort button shows "distance"
      expect(screen.getByText(/Sort:.*distance/i)).toBeInTheDocument();
    });

    it("excludes distance from sort cycle when searchCenter is not provided", () => {
      render(
        <HotelResults
          results={[nearHotel, farHotel]}
          onSelect={vi.fn()}
          onSaveToWishlist={vi.fn()}
          // No searchCenter
        />
      );

      const changeSortButton = screen.getByRole("button", { name: /change sort/i });

      // Cycle through: ai -> price -> rating -> ai (no distance)
      fireEvent.click(changeSortButton); // price
      fireEvent.click(changeSortButton); // rating
      fireEvent.click(changeSortButton); // back to ai

      expect(screen.getByText(/Sort:.*AI Recommended/i)).toBeInTheDocument();
    });

    it("sorts hotels by distance ascending when distance sort is selected", () => {
      render(
        <HotelResults
          results={[farHotel, nearHotel]} // Far hotel first in input
          onSelect={vi.fn()}
          onSaveToWishlist={vi.fn()}
          searchCenter={searchCenter}
        />
      );

      const changeSortButton = screen.getByRole("button", { name: /change sort/i });
      fireEvent.click(changeSortButton); // price
      fireEvent.click(changeSortButton); // rating
      fireEvent.click(changeSortButton); // distance

      // Get hotel headings in order - they appear as h3 elements
      const headings = screen.getAllByRole("heading", { level: 3 });
      const hotelNames = headings.map((h) => h.textContent);

      // Near hotel should be first when sorted by distance ascending
      expect(hotelNames[0]).toBe("Near Hotel");
      expect(hotelNames[1]).toBe("Far Hotel");
    });

    it("places hotels without coordinates at the end when distance sorting", () => {
      render(
        <HotelResults
          results={[noCoordHotel, nearHotel]}
          onSelect={vi.fn()}
          onSaveToWishlist={vi.fn()}
          searchCenter={searchCenter}
        />
      );

      const changeSortButton = screen.getByRole("button", { name: /change sort/i });
      fireEvent.click(changeSortButton); // price
      fireEvent.click(changeSortButton); // rating
      fireEvent.click(changeSortButton); // distance

      // Get hotel headings in order
      const headings = screen.getAllByRole("heading", { level: 3 });
      const hotelNames = headings.map((h) => h.textContent);

      // Hotel with coordinates should come first
      expect(hotelNames[0]).toBe("Near Hotel");
      expect(hotelNames[1]).toBe("No Coord Hotel");
    });
  });
});
