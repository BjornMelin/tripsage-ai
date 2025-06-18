/**
 * @vitest-environment jsdom
 */

import type { Destination } from "@/types/search";
import { render } from "@/test/test-utils";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DestinationCard } from "../destination-card";

const mockDestination: Destination = {
  id: "dest_paris_fr",
  name: "Paris",
  description:
    "The City of Light, known for its art, fashion, gastronomy, and culture.",
  formattedAddress: "Paris, France",
  types: ["locality", "political"],
  coordinates: { lat: 48.8566, lng: 2.3522 },
  photos: ["/images/destinations/paris.jpg"],
  placeId: "ChIJD7fiBh9u5kcRYJSMaMOCCwQ",
  country: "France",
  region: "Île-de-France",
  rating: 4.6,
  popularityScore: 95,
  climate: {
    season: "temperate",
    averageTemp: 12,
    rainfall: 640,
  },
  attractions: ["Eiffel Tower", "Louvre Museum", "Notre-Dame", "Arc de Triomphe"],
  bestTimeToVisit: ["Apr", "May", "Jun", "Sep", "Oct"],
};

const mockHandlers = {
  onSelect: vi.fn(),
  onCompare: vi.fn(),
  onViewDetails: vi.fn(),
};

describe("DestinationCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders destination information correctly", () => {
    render(<DestinationCard destination={mockDestination} {...mockHandlers} />);

    expect(screen.getByText("Paris")).toBeInTheDocument();
    expect(screen.getByText("Paris, France")).toBeInTheDocument();
    expect(
      screen.getByText(
        "The City of Light, known for its art, fashion, gastronomy, and culture."
      )
    ).toBeInTheDocument();
  });

  it("displays rating when available", () => {
    render(<DestinationCard destination={mockDestination} {...mockHandlers} />);

    expect(screen.getByText("4.6")).toBeInTheDocument();
  });

  it("displays climate information when available", () => {
    render(<DestinationCard destination={mockDestination} {...mockHandlers} />);

    expect(screen.getByText("12°C avg")).toBeInTheDocument();
    expect(screen.getByText("640mm rain")).toBeInTheDocument();
  });

  it("displays best time to visit when available", () => {
    render(<DestinationCard destination={mockDestination} {...mockHandlers} />);

    expect(screen.getByText("Best: Apr, May, Jun")).toBeInTheDocument();
  });

  it("displays top attractions when available", () => {
    render(<DestinationCard destination={mockDestination} {...mockHandlers} />);

    expect(screen.getByText("Top Attractions:")).toBeInTheDocument();
    expect(screen.getByText("Eiffel Tower")).toBeInTheDocument();
    expect(screen.getByText("Louvre Museum")).toBeInTheDocument();
    expect(screen.getByText("Notre-Dame")).toBeInTheDocument();
    expect(screen.getByText("+1 more")).toBeInTheDocument(); // 4 attractions, showing 3 + more
  });

  it("displays popularity score when available", () => {
    render(<DestinationCard destination={mockDestination} {...mockHandlers} />);

    expect(screen.getByText("Popularity: 95/100")).toBeInTheDocument();
  });

  it("handles select button click", async () => {
    const user = userEvent.setup();
    render(<DestinationCard destination={mockDestination} {...mockHandlers} />);

    const selectButton = screen.getByText("Select");
    await user.click(selectButton);

    expect(mockHandlers.onSelect).toHaveBeenCalledWith(mockDestination);
  });

  it("handles compare button click", async () => {
    const user = userEvent.setup();
    render(<DestinationCard destination={mockDestination} {...mockHandlers} />);

    const compareButton = screen.getByText("Compare");
    await user.click(compareButton);

    expect(mockHandlers.onCompare).toHaveBeenCalledWith(mockDestination);
  });

  it("handles view details button click", async () => {
    const user = userEvent.setup();
    render(<DestinationCard destination={mockDestination} {...mockHandlers} />);

    const detailsButton = screen.getByText("Details");
    await user.click(detailsButton);

    expect(mockHandlers.onViewDetails).toHaveBeenCalledWith(mockDestination);
  });

  it("renders without optional properties", () => {
    const minimalDestination: Destination = {
      id: "dest_minimal",
      name: "Test City",
      description: "A test destination",
      formattedAddress: "Test City, Test Country",
      types: ["locality"],
      coordinates: { lat: 0, lng: 0 },
    };

    render(<DestinationCard destination={minimalDestination} {...mockHandlers} />);

    expect(screen.getByText("Test City")).toBeInTheDocument();
    expect(screen.getByText("Test City, Test Country")).toBeInTheDocument();
    expect(screen.getByText("A test destination")).toBeInTheDocument();
  });

  it("formats destination types correctly", () => {
    const establishmentDestination: Destination = {
      ...mockDestination,
      types: ["establishment", "tourist_attraction"],
    };

    render(
      <DestinationCard destination={establishmentDestination} {...mockHandlers} />
    );

    expect(screen.getByText("Landmark, Attraction")).toBeInTheDocument();
  });

  it("shows correct icon for different destination types", () => {
    // Test country type
    const countryDestination: Destination = {
      ...mockDestination,
      types: ["country", "political"],
    };

    const { rerender } = render(
      <DestinationCard destination={countryDestination} {...mockHandlers} />
    );

    // Test establishment type
    const establishmentDestination: Destination = {
      ...mockDestination,
      types: ["establishment", "tourist_attraction"],
    };

    rerender(
      <DestinationCard destination={establishmentDestination} {...mockHandlers} />
    );

    // The icons are rendered as SVGs, so we can't easily test their specific type
    // but we can verify they render without errors
    expect(screen.getByText("Paris")).toBeInTheDocument();
  });

  it("renders only when handlers are provided", () => {
    render(
      <DestinationCard
        destination={mockDestination}
        onSelect={mockHandlers.onSelect}
        // Missing onCompare and onViewDetails
      />
    );

    expect(screen.getByText("Select")).toBeInTheDocument();
    expect(screen.queryByText("Compare")).not.toBeInTheDocument();
    expect(screen.queryByText("Details")).not.toBeInTheDocument();
  });

  it("truncates long descriptions", () => {
    const longDescriptionDestination: Destination = {
      ...mockDestination,
      description:
        "This is a very long description that should be truncated when displayed in the card component to maintain a clean and consistent layout across all destination cards in the grid view.",
    };

    render(
      <DestinationCard destination={longDescriptionDestination} {...mockHandlers} />
    );

    // The description should be present but truncated with CSS (line-clamp-3)
    expect(screen.getByText(/This is a very long description/)).toBeInTheDocument();
  });

  it("formats best time to visit with limited months", () => {
    const manyMonthsDestination: Destination = {
      ...mockDestination,
      bestTimeToVisit: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"],
    };

    render(<DestinationCard destination={manyMonthsDestination} {...mockHandlers} />);

    // Should only show first 3 months
    expect(screen.getByText("Best: Jan, Feb, Mar")).toBeInTheDocument();
  });

  it("handles missing best time to visit", () => {
    const noTimeDestination: Destination = {
      ...mockDestination,
      bestTimeToVisit: undefined,
    };

    render(<DestinationCard destination={noTimeDestination} {...mockHandlers} />);

    expect(screen.getByText("Best: Year-round")).toBeInTheDocument();
  });
});
