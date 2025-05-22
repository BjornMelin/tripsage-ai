import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RecentTrips } from "../recent-trips";
import { useTripStore } from "@/stores/trip-store";
import type { Trip } from "@/stores/trip-store";

// Mock the trip store
vi.mock("@/stores/trip-store", () => ({
  useTripStore: vi.fn(),
}));

// Mock Next.js Link component
vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: any) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

const mockTrips: Trip[] = [
  {
    id: "trip-1",
    name: "Tokyo Adventure",
    description: "Exploring Japan's capital city",
    startDate: "2024-06-15T00:00:00Z",
    endDate: "2024-06-22T00:00:00Z",
    destinations: [
      {
        id: "dest-1",
        name: "Tokyo",
        country: "Japan",
        coordinates: { latitude: 35.6762, longitude: 139.6503 },
      },
    ],
    budget: 3000,
    currency: "USD",
    isPublic: false,
    createdAt: "2024-01-15T00:00:00Z",
    updatedAt: "2024-01-16T00:00:00Z",
  },
  {
    id: "trip-2",
    name: "European Tour",
    description: "Multi-city European adventure",
    startDate: "2024-08-01T00:00:00Z",
    endDate: "2024-08-15T00:00:00Z",
    destinations: [
      {
        id: "dest-2",
        name: "Paris",
        country: "France",
      },
      {
        id: "dest-3",
        name: "Rome",
        country: "Italy",
      },
    ],
    budget: 5000,
    currency: "USD",
    isPublic: true,
    createdAt: "2024-01-10T00:00:00Z",
    updatedAt: "2024-01-20T00:00:00Z",
  },
  {
    id: "trip-3",
    name: "Beach Getaway",
    destinations: [],
    isPublic: false,
    createdAt: "2024-01-05T00:00:00Z",
    updatedAt: "2024-01-05T00:00:00Z",
  },
];

describe("RecentTrips", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state correctly", () => {
    (useTripStore as any).mockReturnValue({
      trips: [],
      isLoading: true,
    });

    render(<RecentTrips />);

    expect(screen.getByText("Recent Trips")).toBeInTheDocument();
    expect(screen.getByText("Your latest travel plans")).toBeInTheDocument();
    // Should show skeleton loading
    expect(
      document.querySelectorAll(".animate-pulse").length
    ).toBeGreaterThan(0);
  });

  it("renders empty state when no trips exist", () => {
    (useTripStore as any).mockReturnValue({
      trips: [],
      isLoading: false,
    });

    render(<RecentTrips />);

    expect(screen.getByText("No recent trips yet.")).toBeInTheDocument();
    expect(screen.getByText("Create your first trip")).toBeInTheDocument();
  });

  it("renders trip cards for existing trips", () => {
    (useTripStore as any).mockReturnValue({
      trips: mockTrips,
      isLoading: false,
    });

    render(<RecentTrips />);

    expect(screen.getByText("Tokyo Adventure")).toBeInTheDocument();
    expect(screen.getByText("European Tour")).toBeInTheDocument();
    expect(screen.getByText("Beach Getaway")).toBeInTheDocument();
  });

  it("displays trip details correctly", () => {
    (useTripStore as any).mockReturnValue({
      trips: [mockTrips[0]], // Tokyo Adventure
      isLoading: false,
    });

    render(<RecentTrips />);

    expect(screen.getByText("Tokyo Adventure")).toBeInTheDocument();
    expect(screen.getByText("Tokyo")).toBeInTheDocument();
    expect(screen.getByText("7 days")).toBeInTheDocument();
    expect(screen.getByText("upcoming")).toBeInTheDocument();
    expect(
      screen.getByText("Exploring Japan's capital city")
    ).toBeInTheDocument();
  });

  it("handles trips with multiple destinations", () => {
    (useTripStore as any).mockReturnValue({
      trips: [mockTrips[1]], // European Tour
      isLoading: false,
    });

    render(<RecentTrips />);

    expect(screen.getByText("European Tour")).toBeInTheDocument();
    expect(screen.getByText("Paris (+1 more)")).toBeInTheDocument();
  });

  it("handles trips without dates", () => {
    (useTripStore as any).mockReturnValue({
      trips: [mockTrips[2]], // Beach Getaway
      isLoading: false,
    });

    render(<RecentTrips />);

    expect(screen.getByText("Beach Getaway")).toBeInTheDocument();
    expect(screen.getByText("No destinations")).toBeInTheDocument();
    expect(screen.getByText("draft")).toBeInTheDocument();
  });

  it("limits the number of trips displayed", () => {
    (useTripStore as any).mockReturnValue({
      trips: mockTrips,
      isLoading: false,
    });

    render(<RecentTrips limit={2} />);

    // Should show only 2 trips (sorted by updatedAt desc)
    expect(screen.getByText("European Tour")).toBeInTheDocument(); // Most recent
    expect(screen.getByText("Tokyo Adventure")).toBeInTheDocument(); // Second most recent
    expect(screen.queryByText("Beach Getaway")).not.toBeInTheDocument(); // Oldest
  });

  it("sorts trips by updated date in descending order", () => {
    (useTripStore as any).mockReturnValue({
      trips: mockTrips,
      isLoading: false,
    });

    render(<RecentTrips />);

    const tripCards = screen.getAllByRole("link");
    const tripTitles = tripCards.map((card) => card.textContent);

    // European Tour has the latest updatedAt, so should appear first
    expect(tripTitles[0]).toContain("European Tour");
  });

  it("navigates to trip details when card is clicked", async () => {
    (useTripStore as any).mockReturnValue({
      trips: [mockTrips[0]],
      isLoading: false,
    });

    const user = userEvent.setup();
    render(<RecentTrips />);

    const tripCard = screen.getByRole("link", { name: /Tokyo Adventure/i });
    expect(tripCard).toHaveAttribute("href", "/dashboard/trips/trip-1");
  });

  it("shows 'View All Trips' button when trips exist", () => {
    (useTripStore as any).mockReturnValue({
      trips: mockTrips,
      isLoading: false,
    });

    render(<RecentTrips />);

    const viewAllButton = screen.getByRole("link", { name: /View All Trips/i });
    expect(viewAllButton).toBeInTheDocument();
    expect(viewAllButton).toHaveAttribute("href", "/dashboard/trips");
  });

  it("handles showEmpty prop correctly", () => {
    (useTripStore as any).mockReturnValue({
      trips: [],
      isLoading: false,
    });

    const { rerender } = render(<RecentTrips showEmpty={false} />);

    expect(
      screen.queryByText("Create your first trip")
    ).not.toBeInTheDocument();
    expect(screen.getByText("No recent trips yet.")).toBeInTheDocument();

    rerender(<RecentTrips showEmpty={true} />);

    expect(screen.getByText("Create your first trip")).toBeInTheDocument();
  });

  it("calculates trip status correctly", () => {
    const now = new Date();
    const pastTrip: Trip = {
      ...mockTrips[0],
      startDate: new Date(
        now.getTime() - 10 * 24 * 60 * 60 * 1000
      ).toISOString(), // 10 days ago
      endDate: new Date(now.getTime() - 5 * 24 * 60 * 60 * 1000).toISOString(), // 5 days ago
    };

    const ongoingTrip: Trip = {
      ...mockTrips[0],
      id: "ongoing-trip",
      startDate: new Date(
        now.getTime() - 2 * 24 * 60 * 60 * 1000
      ).toISOString(), // 2 days ago
      endDate: new Date(now.getTime() + 3 * 24 * 60 * 60 * 1000).toISOString(), // 3 days from now
    };

    (useTripStore as any).mockReturnValue({
      trips: [pastTrip, ongoingTrip],
      isLoading: false,
    });

    render(<RecentTrips />);

    expect(screen.getByText("completed")).toBeInTheDocument();
    expect(screen.getByText("ongoing")).toBeInTheDocument();
  });

  it("formats dates correctly", () => {
    (useTripStore as any).mockReturnValue({
      trips: [mockTrips[0]],
      isLoading: false,
    });

    render(<RecentTrips />);

    // Should format dates as "Jun 15, 2024 - Jun 22, 2024"
    expect(screen.getByText(/Jun 15, 2024 - Jun 22, 2024/)).toBeInTheDocument();
  });

  it("handles missing trip description gracefully", () => {
    const tripWithoutDescription: Trip = {
      ...mockTrips[0],
      description: undefined,
    };

    (useTripStore as any).mockReturnValue({
      trips: [tripWithoutDescription],
      isLoading: false,
    });

    render(<RecentTrips />);

    expect(screen.getByText("Tokyo Adventure")).toBeInTheDocument();
    // Description should not be present
    expect(
      screen.queryByText("Exploring Japan's capital city")
    ).not.toBeInTheDocument();
  });
});
