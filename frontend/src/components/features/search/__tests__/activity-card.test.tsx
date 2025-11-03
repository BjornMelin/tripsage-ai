/**
 * @vitest-environment jsdom
 * @fileoverview Tests for ActivityCard component aligned with current UI.
 * Assertions prefer accessibility roles/text over fragile DOM details.
 */

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Activity } from "@/types/search";
import { ActivityCard } from "../activity-card";

const MOCK_ACTIVITY: Activity = {
  coordinates: {
    lat: 40.7829,
    lng: -73.9654,
  },
  date: "2024-07-01",
  description:
    "Discover the hidden gems of Central Park with an expert guide. Learn about the history, architecture, and nature of this iconic NYC landmark.",
  duration: 2.5, // 2.5 hours
  id: "activity-123",
  images: ["https://example.com/image1.jpg"],
  location: "Central Park, New York",
  name: "Central Park Walking Tour",
  price: 45,
  rating: 4.7,
  type: "cultural",
};

const MOCK_ACTIVITY_WITHOUT_IMAGES: Activity = {
  ...MOCK_ACTIVITY,
  id: "activity-456",
  images: [],
};

const MOCK_LONG_DURATION_ACTIVITY: Activity = {
  ...MOCK_ACTIVITY,
  duration: 25, // 25 hours (multi-day)
  id: "activity-789",
  price: 299,
};

describe("ActivityCard", () => {
  it("renders activity information correctly", () => {
    render(<ActivityCard activity={MOCK_ACTIVITY} />);

    expect(screen.getByText("Central Park Walking Tour")).toBeInTheDocument();
    expect(screen.getByText("cultural")).toBeInTheDocument();
    expect(screen.getByText("Central Park, New York")).toBeInTheDocument();
    expect(screen.getAllByText("$45").length).toBeGreaterThan(0);
    expect(screen.getByText("per person")).toBeInTheDocument();
    expect(screen.getByText("(4.7)")).toBeInTheDocument();
    expect(screen.getByText(/discover the hidden gems/i)).toBeInTheDocument();
  });

  it("displays activity image when available", () => {
    render(<ActivityCard activity={MOCK_ACTIVITY} />);

    const image = screen.getByRole("img", { name: /central park walking tour/i });
    expect(image).toBeInTheDocument();
  });

  it("displays placeholder when no images available", () => {
    render(<ActivityCard activity={MOCK_ACTIVITY_WITHOUT_IMAGES} />);

    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByText("Central Park Walking Tour")).toBeInTheDocument();
  });

  it("formats duration correctly for hours", () => {
    render(<ActivityCard activity={MOCK_ACTIVITY} />);

    expect(screen.getByText("2.5 hours")).toBeInTheDocument();
  });

  it("formats duration correctly for minutes", () => {
    const shortActivity = { ...MOCK_ACTIVITY, duration: 0.5 }; // 30 minutes
    render(<ActivityCard activity={shortActivity} />);

    expect(screen.getByText("30 mins")).toBeInTheDocument();
  });

  it("formats duration correctly for single hour", () => {
    const oneHourActivity = { ...MOCK_ACTIVITY, duration: 1 };
    render(<ActivityCard activity={oneHourActivity} />);

    expect(screen.getByText("1 hour")).toBeInTheDocument();
  });

  it("formats duration correctly for multi-day activities", () => {
    render(<ActivityCard activity={MOCK_LONG_DURATION_ACTIVITY} />);

    expect(screen.getByText("1d 1h")).toBeInTheDocument();
  });

  it("formats duration correctly for exact days", () => {
    const exactDayActivity = { ...MOCK_ACTIVITY, duration: 48 }; // 2 days
    render(<ActivityCard activity={exactDayActivity} />);

    expect(screen.getByText("2 days")).toBeInTheDocument();
  });

  it("formats price correctly", () => {
    render(<ActivityCard activity={MOCK_ACTIVITY} />);

    // Price is shown in overlay badge and in primary price area
    expect(screen.getAllByText("$45").length).toBeGreaterThan(0);
  });

  it("formats large price correctly", () => {
    render(<ActivityCard activity={MOCK_LONG_DURATION_ACTIVITY} />);

    expect(screen.getAllByText("$299").length).toBeGreaterThan(0);
  });

  it("renders star rating correctly", () => {
    render(<ActivityCard activity={MOCK_ACTIVITY} />);

    // Check that rating is displayed
    expect(screen.getByText("(4.7)")).toBeInTheDocument();
  });

  it("calls onSelect when Select button is clicked", () => {
    const mockOnSelect = vi.fn();
    render(<ActivityCard activity={MOCK_ACTIVITY} onSelect={mockOnSelect} />);

    const selectButton = screen.getByRole("button", { name: /select/i });
    fireEvent.click(selectButton);

    expect(mockOnSelect).toHaveBeenCalledWith(MOCK_ACTIVITY);
  });

  it("calls onCompare when Compare button is clicked", () => {
    const mockOnCompare = vi.fn();
    render(<ActivityCard activity={MOCK_ACTIVITY} onCompare={mockOnCompare} />);

    const compareButton = screen.getByRole("button", { name: /compare/i });
    fireEvent.click(compareButton);

    expect(mockOnCompare).toHaveBeenCalledWith(MOCK_ACTIVITY);
  });

  it("renders both action buttons", () => {
    render(<ActivityCard activity={MOCK_ACTIVITY} />);

    expect(screen.getByRole("button", { name: /select/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /compare/i })).toBeInTheDocument();
  });

  it("truncates long descriptions", () => {
    const longDescActivity = {
      ...MOCK_ACTIVITY,
      description:
        "This is a very long description that should be truncated after two lines to maintain the card layout and prevent it from becoming too tall with excessive text content that would make the card look unbalanced.",
    };

    render(<ActivityCard activity={longDescActivity} />);

    const description = screen.getByText(/this is a very long description/i);
    expect(description).toBeInTheDocument();
    expect(description).toHaveClass("line-clamp-2");
  });

  it("truncates long activity names", () => {
    const longNameActivity = {
      ...MOCK_ACTIVITY,
      name: "This Is An Extremely Long Activity Name That Should Be Truncated",
    };

    render(<ActivityCard activity={longNameActivity} />);

    const title = screen.getByText(/this is an extremely long activity name/i);
    expect(title).toBeInTheDocument();
    expect(title).toHaveClass("line-clamp-1");
  });

  it("truncates long location names", () => {
    const longLocationActivity = {
      ...MOCK_ACTIVITY,
      location:
        "This Is An Extremely Long Location Name That Should Be Truncated In The Display",
    };

    render(<ActivityCard activity={longLocationActivity} />);

    const location = screen.getByText(/this is an extremely long location/i);
    expect(location).toBeInTheDocument();
    expect(location).toHaveClass("line-clamp-1");
  });

  it("applies hover effects", () => {
    const { container } = render(<ActivityCard activity={MOCK_ACTIVITY} />);
    // Card root has hover:shadow-lg
    const hoverCard = container.querySelector('[class*="hover:shadow-lg"]');
    expect(hoverCard).toBeTruthy();
  });

  it("handles missing coordinates gracefully", () => {
    const activityWithoutCoords = {
      ...MOCK_ACTIVITY,
      coordinates: undefined,
    };

    render(<ActivityCard activity={activityWithoutCoords} />);

    expect(screen.getByText("Central Park Walking Tour")).toBeInTheDocument();
  });

  it("handles zero rating", () => {
    const zeroRatingActivity = {
      ...MOCK_ACTIVITY,
      rating: 0,
    };

    render(<ActivityCard activity={zeroRatingActivity} />);

    expect(screen.getByText("(0)")).toBeInTheDocument();
  });

  it("handles maximum rating", () => {
    const maxRatingActivity = {
      ...MOCK_ACTIVITY,
      rating: 5,
    };

    render(<ActivityCard activity={maxRatingActivity} />);

    expect(screen.getByText("(5)")).toBeInTheDocument();
  });
});
