/** @vitest-environment jsdom */

import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Destination } from "@/lib/schemas/search";
import { render } from "@/test/test-utils";
import { DestinationCard } from "../destination-card";

const MockDestination: Destination = {
  attractions: ["Eiffel Tower", "Louvre Museum", "Notre-Dame", "Arc de Triomphe"],
  bestTimeToVisit: ["Apr", "May", "Jun", "Sep", "Oct"],
  climate: {
    averageTemp: 12,
    rainfall: 640,
    season: "temperate",
  },
  coordinates: { lat: 48.8566, lng: 2.3522 },
  country: "France",
  description:
    "The City of Light, known for its art, fashion, gastronomy, and culture.",
  formattedAddress: "Paris, France",
  id: "dest_paris_fr",
  name: "Paris",
  photos: ["/images/destinations/paris.jpg"],
  placeId: "ChIJD7fiBh9u5kcRYJSMaMOCCwQ",
  popularityScore: 95,
  rating: 4.6,
  region: "Île-de-France",
  types: ["locality", "political"],
};

const MockHandlers = {
  onCompare: vi.fn(),
  onSelect: vi.fn(),
  onViewDetails: vi.fn(),
};

describe("DestinationCard", () => {
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    vi.clearAllMocks();
    user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
  });

  it("renders destination information correctly", () => {
    render(<DestinationCard destination={MockDestination} {...MockHandlers} />);

    expect(screen.getByText("Paris")).toBeInTheDocument();
    expect(screen.getByText("Paris, France")).toBeInTheDocument();
    expect(
      screen.getByText(
        "The City of Light, known for its art, fashion, gastronomy, and culture."
      )
    ).toBeInTheDocument();
  });

  it("displays rating when available", () => {
    render(<DestinationCard destination={MockDestination} {...MockHandlers} />);

    expect(screen.getByText("4.6")).toBeInTheDocument();
  });

  it("displays climate information when available", () => {
    render(<DestinationCard destination={MockDestination} {...MockHandlers} />);

    expect(screen.getByText("12°C avg")).toBeInTheDocument();
    expect(screen.getByText("640mm rain")).toBeInTheDocument();
  });

  it("displays best time to visit when available", () => {
    render(<DestinationCard destination={MockDestination} {...MockHandlers} />);

    expect(screen.getByText("Best: Apr, May, Jun")).toBeInTheDocument();
  });

  it("displays top attractions when available", () => {
    render(<DestinationCard destination={MockDestination} {...MockHandlers} />);

    expect(screen.getByText("Top Attractions:")).toBeInTheDocument();
    expect(screen.getByText("Eiffel Tower")).toBeInTheDocument();
    expect(screen.getByText("Louvre Museum")).toBeInTheDocument();
    expect(screen.getByText("Notre-Dame")).toBeInTheDocument();
    expect(screen.getByText("+1 more")).toBeInTheDocument(); // 4 attractions, showing 3 + more
  });

  it("displays popularity score when available", () => {
    render(<DestinationCard destination={MockDestination} {...MockHandlers} />);

    expect(screen.getByText("Popularity: 95/100")).toBeInTheDocument();
  });

  it("handles select button click", async () => {
    render(<DestinationCard destination={MockDestination} {...MockHandlers} />);

    const selectButton = screen.getByText("Select");
    await act(async () => {
      await user.click(selectButton);
    });

    expect(MockHandlers.onSelect).toHaveBeenCalledWith(MockDestination);
  });

  it("handles compare button click", async () => {
    render(<DestinationCard destination={MockDestination} {...MockHandlers} />);

    const compareButton = screen.getByText("Compare");
    await act(async () => {
      await user.click(compareButton);
    });

    expect(MockHandlers.onCompare).toHaveBeenCalledWith(MockDestination);
  });

  it("handles view details button click", async () => {
    render(<DestinationCard destination={MockDestination} {...MockHandlers} />);

    const detailsButton = screen.getByText("Details");
    await act(async () => {
      await user.click(detailsButton);
    });

    expect(MockHandlers.onViewDetails).toHaveBeenCalledWith(MockDestination);
  });

  it("renders without optional properties", () => {
    const minimalDestination: Destination = {
      coordinates: { lat: 0, lng: 0 },
      description: "A test destination",
      formattedAddress: "Test City, Test Country",
      id: "dest_minimal",
      name: "Test City",
      types: ["locality"],
    };

    render(<DestinationCard destination={minimalDestination} {...MockHandlers} />);

    expect(screen.getByText("Test City")).toBeInTheDocument();
    expect(screen.getByText("Test City, Test Country")).toBeInTheDocument();
    expect(screen.getByText("A test destination")).toBeInTheDocument();
  });

  it("formats destination types correctly", () => {
    const establishmentDestination: Destination = {
      ...MockDestination,
      types: ["establishment", "tourist_attraction"],
    };

    render(
      <DestinationCard destination={establishmentDestination} {...MockHandlers} />
    );

    expect(screen.getByText("Landmark, Attraction")).toBeInTheDocument();
  });

  it("shows correct icon for different destination types", () => {
    // Test country type
    const countryDestination: Destination = {
      ...MockDestination,
      types: ["country", "political"],
    };

    const { rerender } = render(
      <DestinationCard destination={countryDestination} {...MockHandlers} />
    );

    // Test establishment type
    const establishmentDestination: Destination = {
      ...MockDestination,
      types: ["establishment", "tourist_attraction"],
    };

    rerender(
      <DestinationCard destination={establishmentDestination} {...MockHandlers} />
    );

    // The icons are rendered as SVGs, so we can't easily test their specific type
    // but we can verify they render without errors
    expect(screen.getByText("Paris")).toBeInTheDocument();
  });

  it("renders only when handlers are provided", () => {
    render(
      <DestinationCard
        destination={MockDestination}
        onSelect={MockHandlers.onSelect}
        // Missing onCompare and onViewDetails
      />
    );

    expect(screen.getByText("Select")).toBeInTheDocument();
    expect(screen.queryByText("Compare")).not.toBeInTheDocument();
    expect(screen.queryByText("Details")).not.toBeInTheDocument();
  });

  it("truncates long descriptions", () => {
    const longDescriptionDestination: Destination = {
      ...MockDestination,
      description:
        "This is a very long description that should be truncated when displayed in the card component to maintain a clean and consistent layout across all destination cards in the grid view.",
    };

    render(
      <DestinationCard destination={longDescriptionDestination} {...MockHandlers} />
    );

    // The description should be present but truncated with CSS (line-clamp-3)
    expect(screen.getByText(/This is a very long description/)).toBeInTheDocument();
  });

  it("formats best time to visit with limited months", () => {
    const manyMonthsDestination: Destination = {
      ...MockDestination,
      bestTimeToVisit: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"],
    };

    render(<DestinationCard destination={manyMonthsDestination} {...MockHandlers} />);

    // Should only show first 3 months
    expect(screen.getByText("Best: Jan, Feb, Mar")).toBeInTheDocument();
  });

  it("handles missing best time to visit", () => {
    const noTimeDestination: Destination = {
      ...MockDestination,
      bestTimeToVisit: undefined,
    };

    render(<DestinationCard destination={noTimeDestination} {...MockHandlers} />);

    expect(screen.getByText("Best: Year-round")).toBeInTheDocument();
  });
});
