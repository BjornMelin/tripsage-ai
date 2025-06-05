/**
 * @vitest-environment jsdom
 */

import type { Activity } from "@/types/search";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ActivityCard } from "../activity-card";

const mockActivity: Activity = {
  id: "activity-123",
  name: "Central Park Walking Tour",
  type: "cultural",
  location: "Central Park, New York",
  date: "2024-07-01",
  duration: 2.5, // 2.5 hours
  price: 45,
  rating: 4.7,
  description:
    "Discover the hidden gems of Central Park with an expert guide. Learn about the history, architecture, and nature of this iconic NYC landmark.",
  images: ["https://example.com/image1.jpg"],
  coordinates: {
    lat: 40.7829,
    lng: -73.9654,
  },
};

const mockActivityWithoutImages: Activity = {
  ...mockActivity,
  id: "activity-456",
  images: [],
};

const mockLongDurationActivity: Activity = {
  ...mockActivity,
  id: "activity-789",
  duration: 25, // 25 hours (multi-day)
  price: 299,
};

describe("ActivityCard", () => {
  it("renders activity information correctly", () => {
    render(<ActivityCard activity={mockActivity} />);

    expect(screen.getByText("Central Park Walking Tour")).toBeInTheDocument();
    expect(screen.getByText("cultural")).toBeInTheDocument();
    expect(screen.getByText("Central Park, New York")).toBeInTheDocument();
    expect(screen.getByText("$45")).toBeInTheDocument();
    expect(screen.getByText("per person")).toBeInTheDocument();
    expect(screen.getByText("(4.7)")).toBeInTheDocument();
    expect(screen.getByText(/discover the hidden gems/i)).toBeInTheDocument();
  });

  it("displays activity image when available", () => {
    render(<ActivityCard activity={mockActivity} />);

    const image = screen.getByRole("img");
    expect(image).toBeInTheDocument();
    expect(image).toHaveAttribute("src", "https://example.com/image1.jpg");
    expect(image).toHaveAttribute("alt", "Central Park Walking Tour");
  });

  it("displays placeholder when no images available", () => {
    render(<ActivityCard activity={mockActivityWithoutImages} />);

    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByText("Central Park Walking Tour")).toBeInTheDocument();
  });

  it("formats duration correctly for hours", () => {
    render(<ActivityCard activity={mockActivity} />);

    expect(screen.getByText("2.5 hours")).toBeInTheDocument();
  });

  it("formats duration correctly for minutes", () => {
    const shortActivity = { ...mockActivity, duration: 0.5 }; // 30 minutes
    render(<ActivityCard activity={shortActivity} />);

    expect(screen.getByText("30 mins")).toBeInTheDocument();
  });

  it("formats duration correctly for single hour", () => {
    const oneHourActivity = { ...mockActivity, duration: 1 };
    render(<ActivityCard activity={oneHourActivity} />);

    expect(screen.getByText("1 hour")).toBeInTheDocument();
  });

  it("formats duration correctly for multi-day activities", () => {
    render(<ActivityCard activity={mockLongDurationActivity} />);

    expect(screen.getByText("1d 1h")).toBeInTheDocument();
  });

  it("formats duration correctly for exact days", () => {
    const exactDayActivity = { ...mockActivity, duration: 48 }; // 2 days
    render(<ActivityCard activity={exactDayActivity} />);

    expect(screen.getByText("2 days")).toBeInTheDocument();
  });

  it("formats price correctly", () => {
    render(<ActivityCard activity={mockActivity} />);

    expect(screen.getByText("$45")).toBeInTheDocument();
  });

  it("formats large price correctly", () => {
    render(<ActivityCard activity={mockLongDurationActivity} />);

    expect(screen.getByText("$299")).toBeInTheDocument();
  });

  it("renders star rating correctly", () => {
    render(<ActivityCard activity={mockActivity} />);

    // Check that rating is displayed
    expect(screen.getByText("(4.7)")).toBeInTheDocument();
  });

  it("calls onSelect when Select button is clicked", () => {
    const mockOnSelect = vi.fn();
    render(<ActivityCard activity={mockActivity} onSelect={mockOnSelect} />);

    const selectButton = screen.getByRole("button", { name: /select/i });
    fireEvent.click(selectButton);

    expect(mockOnSelect).toHaveBeenCalledWith(mockActivity);
  });

  it("calls onCompare when Compare button is clicked", () => {
    const mockOnCompare = vi.fn();
    render(<ActivityCard activity={mockActivity} onCompare={mockOnCompare} />);

    const compareButton = screen.getByRole("button", { name: /compare/i });
    fireEvent.click(compareButton);

    expect(mockOnCompare).toHaveBeenCalledWith(mockActivity);
  });

  it("renders both action buttons", () => {
    render(<ActivityCard activity={mockActivity} />);

    expect(screen.getByRole("button", { name: /select/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /compare/i })).toBeInTheDocument();
  });

  it("truncates long descriptions", () => {
    const longDescActivity = {
      ...mockActivity,
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
      ...mockActivity,
      name: "This Is An Extremely Long Activity Name That Should Be Truncated",
    };

    render(<ActivityCard activity={longNameActivity} />);

    const title = screen.getByText(/this is an extremely long activity name/i);
    expect(title).toBeInTheDocument();
    expect(title).toHaveClass("line-clamp-1");
  });

  it("truncates long location names", () => {
    const longLocationActivity = {
      ...mockActivity,
      location:
        "This Is An Extremely Long Location Name That Should Be Truncated In The Display",
    };

    render(<ActivityCard activity={longLocationActivity} />);

    const location = screen.getByText(/this is an extremely long location/i);
    expect(location).toBeInTheDocument();
    expect(location).toHaveClass("line-clamp-1");
  });

  it("applies hover effects", () => {
    render(<ActivityCard activity={mockActivity} />);

    const card = screen
      .getByRole("button", { name: /select/i })
      .closest(".group, [class*='hover:']")?.parentElement;
    expect(card).toHaveClass("hover:shadow-lg");
  });

  it("handles missing coordinates gracefully", () => {
    const activityWithoutCoords = {
      ...mockActivity,
      coordinates: undefined,
    };

    render(<ActivityCard activity={activityWithoutCoords} />);

    expect(screen.getByText("Central Park Walking Tour")).toBeInTheDocument();
  });

  it("handles zero rating", () => {
    const zeroRatingActivity = {
      ...mockActivity,
      rating: 0,
    };

    render(<ActivityCard activity={zeroRatingActivity} />);

    expect(screen.getByText("(0)")).toBeInTheDocument();
  });

  it("handles maximum rating", () => {
    const maxRatingActivity = {
      ...mockActivity,
      rating: 5,
    };

    render(<ActivityCard activity={maxRatingActivity} />);

    expect(screen.getByText("(5)")).toBeInTheDocument();
  });
});
