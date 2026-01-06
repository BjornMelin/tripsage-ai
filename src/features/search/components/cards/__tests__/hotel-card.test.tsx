/** @vitest-environment jsdom */

import type { HotelResult } from "@schemas/search";
import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { render } from "@/test/test-utils";
import { HotelCard, PriceHistoryIcon } from "../hotel-card";

function CreateHotel(overrides: Partial<HotelResult> = {}): HotelResult {
  return {
    ai: { personalizedTags: [], reason: "Great value", recommendation: 8 },
    amenities: {
      essential: ["wifi", "pool", "gym", "spa", "parking"],
      premium: [],
      unique: [],
    },
    availability: { flexible: true, roomsLeft: 5, urgency: "low" },
    category: "hotel",
    guestExperience: {
      highlights: ["Excellent breakfast"],
      recentMentions: [],
      vibe: "business",
    },
    id: "h1",
    images: { count: 10, gallery: [], main: "https://example.com/hotel.jpg" },
    location: {
      address: "123 Main St",
      city: "Paris",
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
    sustainability: { certified: true, practices: [], score: 80 },
    userRating: 4.5,
    ...overrides,
  };
}

describe("HotelCard", () => {
  const defaultProps = {
    hotel: CreateHotel(),
    isOptimisticSelecting: false,
    isPending: false,
    isSaved: false,
    onSelect: vi.fn(),
    onToggleWishlist: vi.fn(),
    viewMode: "list" as const,
  };

  it("renders hotel details correctly", () => {
    render(<HotelCard {...defaultProps} />);

    expect(screen.getByRole("heading", { name: "Test Hotel" })).toBeInTheDocument();
    expect(screen.getByText("Center, Paris")).toBeInTheDocument();
    expect(screen.getByText("$200")).toBeInTheDocument();
    expect(screen.getByText("$400 total")).toBeInTheDocument();
    expect(screen.getByText("(120 reviews)")).toBeInTheDocument();
  });

  it("renders AI Pick badge when recommendation >= 8", () => {
    render(<HotelCard {...defaultProps} />);

    expect(screen.getByText("AI Pick")).toBeInTheDocument();
  });

  it("hides AI Pick badge when recommendation < 8", () => {
    const hotel = CreateHotel({
      ai: { personalizedTags: [], reason: "test", recommendation: 5 },
    });
    render(<HotelCard {...defaultProps} hotel={hotel} />);

    expect(screen.queryByText("AI Pick")).not.toBeInTheDocument();
  });

  it("shows AI recommendation panel when recommendation >= 7", () => {
    render(<HotelCard {...defaultProps} />);

    expect(screen.getByText("AI Recommendation: 8/10")).toBeInTheDocument();
    expect(screen.getByText("Great value")).toBeInTheDocument();
  });

  it("hides AI recommendation panel when recommendation < 7", () => {
    const hotel = CreateHotel({
      ai: { personalizedTags: [], reason: "test", recommendation: 5 },
    });
    render(<HotelCard {...defaultProps} hotel={hotel} />);

    expect(screen.queryByText(/AI Recommendation:/)).not.toBeInTheDocument();
  });

  it("renders amenities badges (max 4)", () => {
    render(<HotelCard {...defaultProps} />);

    expect(screen.getByText("wifi")).toBeInTheDocument();
    expect(screen.getByText("pool")).toBeInTheDocument();
    expect(screen.getByText("gym")).toBeInTheDocument();
    expect(screen.getByText("spa")).toBeInTheDocument();
    expect(screen.getByText("+1 more")).toBeInTheDocument();
  });

  it("shows Eco-Certified badge when sustainability certified", () => {
    render(<HotelCard {...defaultProps} />);

    expect(screen.getByText("Eco-Certified")).toBeInTheDocument();
  });

  it("hides Eco-Certified badge when not certified", () => {
    const hotel = CreateHotel({
      sustainability: { certified: false, practices: [], score: 0 },
    });
    render(<HotelCard {...defaultProps} hotel={hotel} />);

    expect(screen.queryByText("Eco-Certified")).not.toBeInTheDocument();
  });

  it("shows All-Inclusive badge when available", () => {
    const hotel = CreateHotel({
      allInclusive: {
        available: true,
        inclusions: ["meals", "drinks"],
        tier: "premium",
      },
    });
    render(<HotelCard {...defaultProps} hotel={hotel} />);

    expect(screen.getByText("All-Inclusive premium")).toBeInTheDocument();
  });

  it("renders guest experience highlight", () => {
    render(<HotelCard {...defaultProps} />);

    expect(screen.getByText('"Excellent breakfast"')).toBeInTheDocument();
  });

  it("shows urgency message when urgency is high", () => {
    const hotel = CreateHotel({
      availability: { flexible: true, roomsLeft: 2, urgency: "high" },
    });
    render(<HotelCard {...defaultProps} hotel={hotel} />);

    expect(screen.getByText("Only 2 rooms left!")).toBeInTheDocument();
  });

  it("hides urgency message when urgency is not high", () => {
    render(<HotelCard {...defaultProps} />);

    expect(screen.queryByText(/Only.*room.*left!/)).not.toBeInTheDocument();
  });

  it("shows deals banner when available", () => {
    const hotel = CreateHotel({
      pricing: {
        ...CreateHotel().pricing,
        deals: {
          description: "Summer Sale",
          originalPrice: 250,
          savings: 50,
          type: "last_minute" as const,
        },
      },
    });
    render(<HotelCard {...defaultProps} hotel={hotel} />);

    expect(screen.getByText("Save $50")).toBeInTheDocument();
    expect(screen.getByText("$250/night")).toBeInTheDocument();
  });

  it("shows Free Cancellation button when flexible", () => {
    render(<HotelCard {...defaultProps} />);

    expect(
      screen.getByRole("button", { name: /free cancellation/i })
    ).toBeInTheDocument();
  });

  it("hides Free Cancellation button when not flexible", () => {
    const hotel = CreateHotel({
      availability: { flexible: false, roomsLeft: 5, urgency: "low" },
    });
    render(<HotelCard {...defaultProps} hotel={hotel} />);

    expect(
      screen.queryByRole("button", { name: /free cancellation/i })
    ).not.toBeInTheDocument();
  });

  it("shows photo count badge", () => {
    render(<HotelCard {...defaultProps} />);

    expect(screen.getByText("10 photos")).toBeInTheDocument();
  });

  it("hides photo count badge when count <= 1", () => {
    const hotel = CreateHotel({ images: { count: 1, gallery: [], main: "" } });
    render(<HotelCard {...defaultProps} hotel={hotel} />);

    expect(screen.queryByText(/photos/)).not.toBeInTheDocument();
  });

  it("calls onSelect when view details is clicked", () => {
    const onSelect = vi.fn();
    render(<HotelCard {...defaultProps} onSelect={onSelect} />);

    fireEvent.click(screen.getByRole("button", { name: /view details/i }));

    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  it("disables view details when isPending", () => {
    render(<HotelCard {...defaultProps} isPending />);

    expect(screen.getByRole("button", { name: /view details/i })).toBeDisabled();
  });

  it("shows Selecting... when isOptimisticSelecting", () => {
    render(<HotelCard {...defaultProps} isOptimisticSelecting />);

    expect(screen.getByRole("button", { name: /selecting/i })).toBeInTheDocument();
  });

  it("calls onToggleWishlist when wishlist button is clicked", () => {
    const onToggleWishlist = vi.fn();
    render(<HotelCard {...defaultProps} onToggleWishlist={onToggleWishlist} />);

    fireEvent.click(screen.getByRole("button", { name: /wishlist/i }));

    expect(onToggleWishlist).toHaveBeenCalledTimes(1);
  });

  it("shows filled heart when isSaved", () => {
    const { container } = render(<HotelCard {...defaultProps} isSaved />);

    const heartIcon = container.querySelector("svg.fill-red-500");
    expect(heartIcon).toBeInTheDocument();
  });

  it("applies opacity when isOptimisticSelecting", () => {
    const { container } = render(<HotelCard {...defaultProps} isOptimisticSelecting />);

    const card = container.querySelector('[class*="opacity-75"]');
    expect(card).toBeInTheDocument();
  });

  it("renders placeholder when no image", () => {
    const hotel = CreateHotel({ images: { count: 0, gallery: [], main: "" } });
    render(<HotelCard {...defaultProps} hotel={hotel} />);

    expect(screen.getByText("No image")).toBeInTheDocument();
  });

  it("renders different layout for grid view", () => {
    const { container } = render(<HotelCard {...defaultProps} viewMode="grid" />);

    const cardContent = container.querySelector('[class*="flex-col"]');
    expect(cardContent).toBeInTheDocument();
  });

  it("handles unknown district gracefully", () => {
    const hotel = CreateHotel({
      location: { address: "123 Main St", city: "Paris", landmarks: [] },
    });
    render(<HotelCard {...defaultProps} hotel={hotel} />);

    expect(screen.getByText("Unknown district, Paris")).toBeInTheDocument();
  });

  it("handles unknown city gracefully", () => {
    const hotel = CreateHotel({
      location: { address: "123 Main St", district: "Center", landmarks: [] },
    });
    render(<HotelCard {...defaultProps} hotel={hotel} />);

    expect(screen.getByText("Center, Unknown city")).toBeInTheDocument();
  });
});

describe("PriceHistoryIcon", () => {
  it("renders down icon for falling prices", () => {
    const { container } = render(<PriceHistoryIcon trend="falling" />);
    const icon = container.querySelector("svg");
    expect(icon).toHaveClass("rotate-180", "text-green-500");
  });

  it("renders up icon for rising prices", () => {
    const { container } = render(<PriceHistoryIcon trend="rising" />);
    const icon = container.querySelector("svg");
    expect(icon).toHaveClass("text-red-500");
    expect(icon).not.toHaveClass("rotate-180");
  });

  it("renders nothing for stable prices", () => {
    const { container } = render(<PriceHistoryIcon trend="stable" />);
    expect(container.querySelector("svg")).toBeNull();
  });
});
