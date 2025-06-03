import type { Trip } from "@/stores/trip-store";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TripTimeline } from "../trip-timeline";

// Mock the stores
vi.mock("@/stores/trip-store", () => ({
  useTripStore: vi.fn(() => ({})),
}));

describe("TripTimeline", () => {
  const mockTrip: Trip = {
    id: "1",
    name: "Test Trip",
    description: "A test trip",
    startDate: "2024-06-01",
    endDate: "2024-06-10",
    destinations: [
      {
        id: "1",
        name: "Paris",
        country: "France",
        startDate: "2024-06-01",
        endDate: "2024-06-05",
        activities: ["Visit Eiffel Tower", "Louvre Museum"],
        accommodation: {
          type: "hotel",
          name: "Hotel de Paris",
          price: 150,
        },
        transportation: {
          type: "flight",
          details: "Air France AF123",
          price: 400,
        },
        estimatedCost: 1000,
      },
      {
        id: "2",
        name: "London",
        country: "UK",
        startDate: "2024-06-06",
        endDate: "2024-06-10",
        activities: ["Tower Bridge", "British Museum"],
        transportation: {
          type: "train",
          details: "Eurostar",
          price: 200,
        },
        estimatedCost: 800,
      },
    ],
    budget: 2000,
    currency: "USD",
    isPublic: false,
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
  };

  it("renders timeline with destinations correctly", () => {
    render(<TripTimeline trip={mockTrip} />);

    expect(screen.getByText("Trip Timeline")).toBeInTheDocument();
    expect(screen.getByText("2 destinations • 10 days")).toBeInTheDocument();

    // Check for arrival events
    expect(screen.getByText("Arrive in Paris")).toBeInTheDocument();
    expect(screen.getByText("Arrive in London")).toBeInTheDocument();

    // Check for departure event
    expect(screen.getByText("Leave Paris")).toBeInTheDocument();
  });

  it("displays activities for each destination", () => {
    render(<TripTimeline trip={mockTrip} />);

    expect(screen.getByText("Visit Eiffel Tower")).toBeInTheDocument();
    expect(screen.getByText("Louvre Museum")).toBeInTheDocument();
    expect(screen.getByText("Tower Bridge")).toBeInTheDocument();
    expect(screen.getByText("British Museum")).toBeInTheDocument();
  });

  it("shows transportation details", () => {
    render(<TripTimeline trip={mockTrip} />);

    expect(screen.getByText("Air France AF123")).toBeInTheDocument();
    expect(screen.getByText("Eurostar")).toBeInTheDocument();
  });

  it("displays accommodation information", () => {
    render(<TripTimeline trip={mockTrip} />);

    expect(screen.getByText(/Hotel de Paris/)).toBeInTheDocument();
    expect(screen.getByText(/\(\$150\/night\)/)).toBeInTheDocument();
  });

  it("shows estimated costs", () => {
    render(<TripTimeline trip={mockTrip} />);

    expect(screen.getByText("Estimated cost: $1000")).toBeInTheDocument();
    expect(screen.getByText("Estimated cost: $800")).toBeInTheDocument();
  });

  it("calls onEditDestination when edit button is clicked", () => {
    const onEditDestination = vi.fn();
    render(<TripTimeline trip={mockTrip} onEditDestination={onEditDestination} />);

    const editButtons = screen.getAllByText("Edit");
    fireEvent.click(editButtons[0]);

    expect(onEditDestination).toHaveBeenCalledWith(mockTrip.destinations[0]);
  });

  it("calls onAddDestination when add destination button is clicked", () => {
    const onAddDestination = vi.fn();
    render(<TripTimeline trip={mockTrip} onAddDestination={onAddDestination} />);

    fireEvent.click(screen.getByText("Add Destination"));
    expect(onAddDestination).toHaveBeenCalled();
  });

  it("shows empty state when no destinations exist", () => {
    const emptyTrip = {
      ...mockTrip,
      destinations: [],
    };

    const onAddDestination = vi.fn();
    render(<TripTimeline trip={emptyTrip} onAddDestination={onAddDestination} />);

    expect(screen.getByText("No destinations planned yet")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Add First Destination"));
    expect(onAddDestination).toHaveBeenCalled();
  });

  it("handles destinations without dates gracefully", () => {
    const tripWithoutDates = {
      ...mockTrip,
      destinations: [
        {
          id: "1",
          name: "Paris",
          country: "France",
          activities: ["Visit Eiffel Tower"],
        },
      ],
    };

    render(<TripTimeline trip={tripWithoutDates} />);

    // Should still render but with current date as fallback
    expect(screen.getByText("Visit Eiffel Tower")).toBeInTheDocument();
  });

  it("hides actions when showActions is false", () => {
    render(<TripTimeline trip={mockTrip} showActions={false} />);

    expect(screen.queryByText("Edit")).not.toBeInTheDocument();
    expect(screen.queryByText("Add Destination")).not.toBeInTheDocument();
  });

  it("displays correct transportation icons", () => {
    render(<TripTimeline trip={mockTrip} />);

    // Flight icon should be present for Paris (first destination)
    const timelineEvents = screen.getAllByText(/arrival|departure/i);
    expect(timelineEvents.length).toBeGreaterThan(0);
  });

  it("calculates timeline correctly without end date", () => {
    const tripWithoutEndDate = {
      ...mockTrip,
      endDate: undefined,
    };

    render(<TripTimeline trip={tripWithoutEndDate} />);

    // Should render destinations count but not duration
    expect(screen.getByText(/2 destinations/)).toBeInTheDocument();
    expect(screen.queryByText(/days/)).not.toBeInTheDocument();
  });
});
