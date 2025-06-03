import type { Trip } from "@/stores/trip-store";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TripCard } from "../trip-card";

// Mock the stores
vi.mock("@/stores/trip-store", () => ({
  useTripStore: vi.fn(() => ({})),
}));

vi.mock("@/stores/budget-store", () => ({
  useBudgetStore: vi.fn(() => ({
    budgetsByTrip: {},
  })),
}));

// Mock Next.js Link
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

describe("TripCard", () => {
  const mockTrip: Trip = {
    id: "1",
    name: "Test Trip",
    description: "A test trip description",
    startDate: "2024-06-01",
    endDate: "2024-06-10",
    destinations: [
      {
        id: "1",
        name: "Paris",
        country: "France",
      },
    ],
    budget: 2000,
    currency: "USD",
    isPublic: false,
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
  };

  it("renders trip information correctly", () => {
    render(<TripCard trip={mockTrip} />);

    expect(screen.getByText("Test Trip")).toBeInTheDocument();
    expect(screen.getByText("A test trip description")).toBeInTheDocument();
    expect(screen.getByText("Paris")).toBeInTheDocument();
    expect(screen.getByText(/Budget: \$2,000\.00/)).toBeInTheDocument();
  });

  it("shows correct status for upcoming trip", () => {
    const futureTrip = {
      ...mockTrip,
      startDate: "2025-06-01",
      endDate: "2025-06-10",
    };

    render(<TripCard trip={futureTrip} />);
    expect(screen.getByText("Upcoming")).toBeInTheDocument();
  });

  it("shows correct status for draft trip", () => {
    const draftTrip = {
      ...mockTrip,
      startDate: undefined,
      endDate: undefined,
    };

    render(<TripCard trip={draftTrip} />);
    expect(screen.getByText("Draft")).toBeInTheDocument();
  });

  it("displays multiple destinations correctly", () => {
    const multiDestTrip = {
      ...mockTrip,
      destinations: [
        { id: "1", name: "Paris", country: "France" },
        { id: "2", name: "London", country: "UK" },
        { id: "3", name: "Rome", country: "Italy" },
      ],
    };

    render(<TripCard trip={multiDestTrip} />);
    expect(screen.getByText("Paris + 2 more")).toBeInTheDocument();
  });

  it("shows public badge when trip is public", () => {
    const publicTrip = { ...mockTrip, isPublic: true };

    render(<TripCard trip={publicTrip} />);
    expect(screen.getByText("Public")).toBeInTheDocument();
  });

  it("calls onEdit when edit button is clicked", () => {
    const onEdit = vi.fn();
    render(<TripCard trip={mockTrip} onEdit={onEdit} />);

    fireEvent.click(screen.getByText("Edit"));
    expect(onEdit).toHaveBeenCalledWith(mockTrip);
  });

  it("calls onDelete when delete button is clicked", () => {
    const onDelete = vi.fn();
    render(<TripCard trip={mockTrip} onDelete={onDelete} />);

    fireEvent.click(screen.getByText("Delete"));
    expect(onDelete).toHaveBeenCalledWith(mockTrip.id);
  });

  it("calculates trip duration correctly", () => {
    render(<TripCard trip={mockTrip} />);
    expect(screen.getByText(/\(10 days\)/)).toBeInTheDocument();
  });

  it("handles missing dates gracefully", () => {
    const tripWithoutDates = {
      ...mockTrip,
      startDate: undefined,
      endDate: undefined,
    };

    render(<TripCard trip={tripWithoutDates} />);
    expect(screen.getByText("Not set - Not set")).toBeInTheDocument();
  });

  it("renders view details link with correct href", () => {
    render(<TripCard trip={mockTrip} />);

    const viewDetailsLink = screen.getByText("View Details").closest("a");
    expect(viewDetailsLink).toHaveAttribute("href", "/dashboard/trips/1");
  });
});
