import type { Trip } from "@/stores/trip-store";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import TripsPage from "../page";

// Mock the stores
const mockTrips: Trip[] = [
  {
    id: "1",
    title: "Paris Adventure",
    name: "Paris Adventure",
    description: "A romantic trip to Paris",
    startDate: "2024-06-01",
    endDate: "2024-06-10",
    destinations: [{ id: "1", name: "Paris", country: "France" }],
    budget: 2000,
    currency: "USD",
    isPublic: false,
    createdAt: "2024-01-01T00:00:00Z",
    updatedAt: "2024-01-01T00:00:00Z",
  },
  {
    id: "2",
    title: "Tokyo Journey",
    name: "Tokyo Journey",
    description: "Exploring modern Japan",
    startDate: "2025-03-15",
    endDate: "2025-03-25",
    destinations: [{ id: "2", name: "Tokyo", country: "Japan" }],
    budget: 3000,
    currency: "USD",
    isPublic: true,
    createdAt: "2024-01-02T00:00:00Z",
    updatedAt: "2024-01-02T00:00:00Z",
  },
  {
    id: "3",
    title: "Draft Trip",
    name: "Draft Trip",
    description: "Planning stage",
    destinations: [],
    isPublic: false,
    createdAt: "2024-01-03T00:00:00Z",
    updatedAt: "2024-01-03T00:00:00Z",
  },
];

vi.mock("@/stores/trip-store", () => ({
  useTripStore: vi.fn(() => ({
    trips: mockTrips,
    createTrip: vi.fn(),
    deleteTrip: vi.fn(),
  })),
}));

// Mock the TripCard component
vi.mock("@/components/features/trips", () => ({
  TripCard: ({ trip, onDelete }: { trip: Trip; onDelete?: (id: string) => void }) => (
    <div data-testid={`trip-card-${trip.id}`}>
      <h3>{trip.name}</h3>
      <p>{trip.description}</p>
      {onDelete && <button onClick={() => onDelete(trip.id)}>Delete Trip</button>}
    </div>
  ),
}));

describe("TripsPage", () => {
  it("renders trips correctly", () => {
    render(<TripsPage />);

    expect(screen.getByText("My Trips")).toBeInTheDocument();
    expect(screen.getByText("3 trips in your collection")).toBeInTheDocument();

    expect(screen.getByText("Paris Adventure")).toBeInTheDocument();
    expect(screen.getByText("Tokyo Journey")).toBeInTheDocument();
    expect(screen.getByText("Draft Trip")).toBeInTheDocument();
  });

  it("displays status counts correctly", () => {
    render(<TripsPage />);

    // Should show counts for each status
    const statusCards = screen.getAllByText(/^\d+$/);
    expect(statusCards).toHaveLength(4); // draft, upcoming, active, completed
  });

  it("filters trips by search query", async () => {
    render(<TripsPage />);

    const searchInput = screen.getByPlaceholderText("Search trips, destinations...");
    fireEvent.change(searchInput, { target: { value: "Paris" } });

    await waitFor(() => {
      expect(screen.getByText("Paris Adventure")).toBeInTheDocument();
      expect(screen.queryByText("Tokyo Journey")).not.toBeInTheDocument();
      expect(screen.queryByText("Draft Trip")).not.toBeInTheDocument();
    });
  });

  it("filters trips by status", async () => {
    render(<TripsPage />);

    // Find and click the filter dropdown
    const filterSelect = screen.getByRole("combobox");
    fireEvent.click(filterSelect);

    // Select "Draft" filter
    const draftOption = screen.getByText("Draft");
    fireEvent.click(draftOption);

    await waitFor(() => {
      expect(screen.getByText("Draft Trip")).toBeInTheDocument();
      expect(screen.queryByText("Paris Adventure")).not.toBeInTheDocument();
      expect(screen.queryByText("Tokyo Journey")).not.toBeInTheDocument();
    });
  });

  it("sorts trips correctly", async () => {
    render(<TripsPage />);

    // Initially should be sorted by date (latest first)
    const tripCards = screen.getAllByTestId(/trip-card-/);
    expect(tripCards[0]).toHaveAttribute("data-testid", "trip-card-3"); // Draft Trip (latest)
  });

  it("switches between grid and list view modes", () => {
    render(<TripsPage />);

    const gridButton = screen.getByRole("button", { name: /grid/i });
    const listButton = screen.getByRole("button", { name: /list/i });

    // Initially grid should be active
    expect(gridButton).toHaveClass("default");

    // Switch to list view
    fireEvent.click(listButton);
    expect(listButton).toHaveClass("default");
  });

  it("calls createTrip when create button is clicked", async () => {
    const mockCreateTrip = vi.fn();

    vi.mocked(vi.mocked(require("@/stores/trip-store").useTripStore)).mockReturnValue({
      trips: mockTrips,
      createTrip: mockCreateTrip,
      deleteTrip: vi.fn(),
    });

    render(<TripsPage />);

    fireEvent.click(screen.getByText("Create Trip"));

    expect(mockCreateTrip).toHaveBeenCalledWith({
      name: "New Trip",
      description: "",
      destinations: [],
      isPublic: false,
    });
  });

  it("calls deleteTrip when delete is confirmed", async () => {
    const mockDeleteTrip = vi.fn();

    // Mock window.confirm
    global.confirm = vi.fn(() => true);

    vi.mocked(vi.mocked(require("@/stores/trip-store").useTripStore)).mockReturnValue({
      trips: mockTrips,
      createTrip: vi.fn(),
      deleteTrip: mockDeleteTrip,
    });

    render(<TripsPage />);

    const deleteButtons = screen.getAllByText("Delete Trip");
    fireEvent.click(deleteButtons[0]);

    expect(global.confirm).toHaveBeenCalledWith(
      "Are you sure you want to delete this trip?"
    );
    expect(mockDeleteTrip).toHaveBeenCalledWith("1");
  });

  it("shows empty state when no trips exist", () => {
    vi.mocked(vi.mocked(require("@/stores/trip-store").useTripStore)).mockReturnValue({
      trips: [],
      createTrip: vi.fn(),
      deleteTrip: vi.fn(),
    });

    render(<TripsPage />);

    expect(screen.getByText("No trips yet")).toBeInTheDocument();
    expect(screen.getByText("Create Your First Trip")).toBeInTheDocument();
  });

  it("shows no results when search/filter returns empty", async () => {
    render(<TripsPage />);

    const searchInput = screen.getByPlaceholderText("Search trips, destinations...");
    fireEvent.change(searchInput, { target: { value: "NonexistentTrip" } });

    await waitFor(() => {
      expect(screen.getByText("No trips found")).toBeInTheDocument();
      expect(screen.getByText("Clear Filters")).toBeInTheDocument();
    });
  });

  it("clears filters when clear button is clicked", async () => {
    render(<TripsPage />);

    // Apply a search filter
    const searchInput = screen.getByPlaceholderText("Search trips, destinations...");
    fireEvent.change(searchInput, { target: { value: "NonexistentTrip" } });

    await waitFor(() => {
      expect(screen.getByText("No trips found")).toBeInTheDocument();
    });

    // Click clear filters
    fireEvent.click(screen.getByText("Clear Filters"));

    await waitFor(() => {
      expect(searchInput).toHaveValue("");
      expect(screen.getByText("Paris Adventure")).toBeInTheDocument();
    });
  });

  it("displays correct trip count in header", () => {
    render(<TripsPage />);

    expect(screen.getByText("3 trips in your collection")).toBeInTheDocument();
  });

  it("handles singular trip count correctly", () => {
    vi.mocked(vi.mocked(require("@/stores/trip-store").useTripStore)).mockReturnValue({
      trips: [mockTrips[0]],
      createTrip: vi.fn(),
      deleteTrip: vi.fn(),
    });

    render(<TripsPage />);

    expect(screen.getByText("1 trip in your collection")).toBeInTheDocument();
  });
});
