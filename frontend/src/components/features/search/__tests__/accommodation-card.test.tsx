import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { AccommodationCard } from "../accommodation-card";
import type { Accommodation } from "@/types/search";

describe("AccommodationCard", () => {
  const mockAccommodation: Accommodation = {
    id: "1",
    name: "Luxury Beach Resort",
    type: "Resort",
    location: "Miami Beach, FL",
    checkIn: "2024-03-15",
    checkOut: "2024-03-18",
    pricePerNight: 250,
    totalPrice: 750,
    rating: 4.8,
    amenities: [
      "wifi",
      "pool",
      "gym",
      "spa",
      "restaurant",
      "parking",
      "breakfast",
    ],
    images: ["https://example.com/image1.jpg"],
    coordinates: {
      lat: 25.7907,
      lng: -80.13,
    },
  };

  it("should render accommodation details correctly", () => {
    render(<AccommodationCard accommodation={mockAccommodation} />);

    expect(screen.getByText("Luxury Beach Resort")).toBeInTheDocument();
    expect(screen.getByText("Miami Beach, FL")).toBeInTheDocument();
    expect(screen.getByText("4.8")).toBeInTheDocument();
    expect(screen.getByText("Resort")).toBeInTheDocument();
    expect(screen.getByText("$250")).toBeInTheDocument();
    expect(screen.getByText("/night")).toBeInTheDocument();
    expect(screen.getByText("Total: $750 (3 nights)")).toBeInTheDocument();
  });

  it("should display amenities with icons", () => {
    render(<AccommodationCard accommodation={mockAccommodation} />);

    // First 6 amenities should be displayed
    expect(screen.getByText("wifi")).toBeInTheDocument();
    expect(screen.getByText("pool")).toBeInTheDocument();
    expect(screen.getByText("gym")).toBeInTheDocument();
    expect(screen.getByText("spa")).toBeInTheDocument();
    expect(screen.getByText("restaurant")).toBeInTheDocument();
    expect(screen.getByText("parking")).toBeInTheDocument();

    // Should show "+1 more" for the 7th amenity
    expect(screen.getByText("+1 more")).toBeInTheDocument();
  });

  it("should handle select button click", () => {
    const mockOnSelect = vi.fn();
    render(
      <AccommodationCard
        accommodation={mockAccommodation}
        onSelect={mockOnSelect}
      />
    );

    const selectButton = screen.getByText("View Details");
    fireEvent.click(selectButton);

    expect(mockOnSelect).toHaveBeenCalledWith(mockAccommodation);
  });

  it("should handle compare button click", () => {
    const mockOnCompare = vi.fn();
    render(
      <AccommodationCard
        accommodation={mockAccommodation}
        onCompare={mockOnCompare}
      />
    );

    const compareButton = screen.getByText("Compare");
    fireEvent.click(compareButton);

    expect(mockOnCompare).toHaveBeenCalledWith(mockAccommodation);
  });

  it("should display placeholder when no image", () => {
    const accommodationWithoutImage = {
      ...mockAccommodation,
      images: [],
    };

    render(<AccommodationCard accommodation={accommodationWithoutImage} />);

    expect(screen.getByText("No image")).toBeInTheDocument();
  });

  it("should calculate nights correctly", () => {
    const accommodationWithDifferentDates = {
      ...mockAccommodation,
      checkIn: "2024-03-10",
      checkOut: "2024-03-17",
      totalPrice: 1750,
    };

    render(
      <AccommodationCard accommodation={accommodationWithDifferentDates} />
    );

    expect(screen.getByText("Total: $1750 (7 nights)")).toBeInTheDocument();
  });

  it("should render without action buttons when no handlers provided", () => {
    render(<AccommodationCard accommodation={mockAccommodation} />);

    expect(screen.queryByText("View Details")).not.toBeInTheDocument();
    expect(screen.queryByText("Compare")).not.toBeInTheDocument();
  });

  it("should display star icon with rating", () => {
    render(<AccommodationCard accommodation={mockAccommodation} />);

    const ratingElement = screen.getByText("4.8");
    expect(ratingElement).toBeInTheDocument();

    // Check if star icon is rendered (through the parent element)
    const starContainer = ratingElement.parentElement;
    expect(starContainer).toHaveClass("flex", "items-center", "gap-1");
  });

  it("should format amenity names correctly", () => {
    const accommodationWithUnderscoredAmenity = {
      ...mockAccommodation,
      amenities: ["free_wifi", "swimming_pool"],
    };

    render(
      <AccommodationCard accommodation={accommodationWithUnderscoredAmenity} />
    );

    expect(screen.getByText("free wifi")).toBeInTheDocument();
    expect(screen.getByText("swimming pool")).toBeInTheDocument();
  });
});
