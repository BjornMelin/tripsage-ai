import { useTrips } from "@/hooks/use-trips";
import type { Trip } from "@/stores/trip-store";
import { renderWithProviders } from "@/test/test-utils";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RecentTrips } from "../recent-trips";

// Mock the useTrips hook
vi.mock("@/hooks/use-trips", () => ({
  useTrips: vi.fn(),
}));

// Mock Next.js Link component
vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: any) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

// Mock trips as they come from the API
const mockTrips: any[] = [
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
    created_at: "2024-01-15T00:00:00Z",
    updated_at: "2024-01-16T00:00:00Z",
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
    created_at: "2024-01-10T00:00:00Z",
    updated_at: "2024-01-20T00:00:00Z",
  },
  {
    id: "trip-3",
    name: "Beach Getaway",
    destinations: [],
    isPublic: false,
    created_at: "2024-01-05T00:00:00Z",
    updated_at: "2024-01-05T00:00:00Z",
  },
];

describe("RecentTrips", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state correctly", () => {
    vi.mocked(useTrips).mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithProviders(<RecentTrips />);

    expect(screen.getByText("Recent Trips")).toBeInTheDocument();
    expect(screen.getByText("Your latest travel plans")).toBeInTheDocument();
    // Should show skeleton loading
    expect(document.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0);
  });

  it("renders empty state when no trips exist", () => {
    vi.mocked(useTrips).mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithProviders(<RecentTrips />);

    expect(screen.getByText("No recent trips yet.")).toBeInTheDocument();
    expect(screen.getByText("Create your first trip")).toBeInTheDocument();
  });

  it("renders trip cards for existing trips", () => {
    vi.mocked(useTrips).mockReturnValue({
      data: { items: mockTrips, total: mockTrips.length },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithProviders(<RecentTrips />);

    expect(screen.getByText("Tokyo Adventure")).toBeInTheDocument();
    expect(screen.getByText("European Tour")).toBeInTheDocument();
    expect(screen.getByText("Beach Getaway")).toBeInTheDocument();
  });

  it("displays trip details correctly", () => {
    // Clear any previous mocks
    vi.clearAllMocks();
    
    vi.mocked(useTrips).mockReturnValue({
      data: { items: [mockTrips[0]], total: 1 }, // Tokyo Adventure
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithProviders(<RecentTrips />);

    expect(screen.getByText("Tokyo Adventure")).toBeInTheDocument();
    expect(screen.getByText("Tokyo")).toBeInTheDocument();
    expect(screen.getByText("7 days")).toBeInTheDocument();
    expect(screen.getByText("upcoming")).toBeInTheDocument();
    expect(screen.getByText("Exploring Japan's capital city")).toBeInTheDocument();
  });

  it("handles trips with multiple destinations", () => {
    vi.mocked(useTrips).mockReturnValue({
      data: { items: [mockTrips[1]], total: 1 }, // European Tour
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithProviders(<RecentTrips />);

    expect(screen.getByText("European Tour")).toBeInTheDocument();
    expect(screen.getByText("Paris (+1 more)")).toBeInTheDocument();
  });

  it("handles trips without dates", () => {
    vi.mocked(useTrips).mockReturnValue({
      data: { items: [mockTrips[2]], total: 1 }, // Beach Getaway
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithProviders(<RecentTrips />);

    expect(screen.getByText("Beach Getaway")).toBeInTheDocument();
    expect(screen.getByText("No destinations")).toBeInTheDocument();
    expect(screen.getByText("draft")).toBeInTheDocument();
  });

  it("limits the number of trips displayed", () => {
    vi.mocked(useTrips).mockReturnValue({
      data: { items: mockTrips, total: mockTrips.length },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithProviders(<RecentTrips limit={2} />);

    // Should show only 2 trips (sorted by updatedAt desc)
    expect(screen.getByText("European Tour")).toBeInTheDocument(); // Most recent
    expect(screen.getByText("Tokyo Adventure")).toBeInTheDocument(); // Second most recent
    expect(screen.queryByText("Beach Getaway")).not.toBeInTheDocument(); // Oldest
  });

  it("sorts trips by updated date in descending order", () => {
    vi.mocked(useTrips).mockReturnValue({
      data: { items: mockTrips, total: mockTrips.length },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithProviders(<RecentTrips />);

    const tripCards = screen.getAllByRole("link");
    const tripTitles = tripCards.map((card) => card.textContent);

    // European Tour has the latest updatedAt, so should appear first
    expect(tripTitles[0]).toContain("European Tour");
  });

  it("navigates to trip details when card is clicked", async () => {
    vi.mocked(useTrips).mockReturnValue({
      data: { items: [mockTrips[0]], total: 1 },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    const user = userEvent.setup();
    renderWithProviders(<RecentTrips />);

    const tripCard = screen.getByRole("link", { name: /Tokyo Adventure/i });
    expect(tripCard).toHaveAttribute("href", "/dashboard/trips/trip-1");
  });

  it("shows 'View All Trips' button when trips exist", () => {
    vi.mocked(useTrips).mockReturnValue({
      data: { items: mockTrips, total: mockTrips.length },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithProviders(<RecentTrips />);

    const viewAllButton = screen.getByRole("link", { name: /View All Trips/i });
    expect(viewAllButton).toBeInTheDocument();
    expect(viewAllButton).toHaveAttribute("href", "/dashboard/trips");
  });

  it("handles showEmpty prop correctly", () => {
    vi.mocked(useTrips).mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    const { rerender } = renderWithProviders(<RecentTrips showEmpty={false} />);

    expect(screen.queryByText("Create your first trip")).not.toBeInTheDocument();
    expect(screen.getByText("No recent trips yet.")).toBeInTheDocument();

    rerender(<RecentTrips showEmpty={true} />);

    expect(screen.getByText("Create your first trip")).toBeInTheDocument();
  });

  it("calculates trip status correctly", () => {
    const now = new Date();
    const pastTrip: Trip = {
      ...mockTrips[0],
      startDate: new Date(now.getTime() - 10 * 24 * 60 * 60 * 1000).toISOString(), // 10 days ago
      endDate: new Date(now.getTime() - 5 * 24 * 60 * 60 * 1000).toISOString(), // 5 days ago
    };

    const ongoingTrip: Trip = {
      ...mockTrips[0],
      id: "ongoing-trip",
      startDate: new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000).toISOString(), // 2 days ago
      endDate: new Date(now.getTime() + 3 * 24 * 60 * 60 * 1000).toISOString(), // 3 days from now
    };

    vi.mocked(useTrips).mockReturnValue({
      data: { items: [pastTrip, ongoingTrip], total: 2 },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithProviders(<RecentTrips />);

    expect(screen.getByText("completed")).toBeInTheDocument();
    expect(screen.getByText("ongoing")).toBeInTheDocument();
  });

  it("formats dates correctly", () => {
    vi.mocked(useTrips).mockReturnValue({
      data: { items: [mockTrips[0]], total: 1 },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithProviders(<RecentTrips />);

    // Should format dates as "Jun 15, 2024 - Jun 22, 2024"
    expect(screen.getByText(/Jun 15, 2024 - Jun 22, 2024/)).toBeInTheDocument();
  });

  it("handles missing trip description gracefully", () => {
    const tripWithoutDescription: Trip = {
      ...mockTrips[0],
      description: undefined,
    };

    vi.mocked(useTrips).mockReturnValue({
      data: { items: [tripWithoutDescription], total: 1 },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as any);

    renderWithProviders(<RecentTrips />);

    expect(screen.getByText("Tokyo Adventure")).toBeInTheDocument();
    // Description should not be present
    expect(
      screen.queryByText("Exploring Japan's capital city")
    ).not.toBeInTheDocument();
  });
});
