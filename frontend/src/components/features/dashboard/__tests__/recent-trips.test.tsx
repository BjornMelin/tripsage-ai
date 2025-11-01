/**
 * @fileoverview Stable tests for RecentTrips aligned with current UI.
 * Uses per-test module resets and doMock to avoid cross-test interference.
 */
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Trip } from "@/stores/trip-store";
import { renderWithProviders } from "@/test/test-utils";

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: any) => (
    // eslint-disable-next-line jsx-a11y/anchor-is-valid
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

const mockTrips: any[] = [
  {
    id: "trip-1",
    name: "Tokyo Adventure",
    description: "Exploring Japan's capital city",
    startDate: "2024-06-15T00:00:00Z",
    endDate: "2024-06-22T00:00:00Z",
    destinations: [{ id: "dest-1", name: "Tokyo", country: "Japan" }],
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
      { id: "dest-2", name: "Paris", country: "France" },
      { id: "dest-3", name: "Rome", country: "Italy" },
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

async function doMockTrips(items: any[] | null, isLoading = false) {
  vi.resetModules();
  vi.doMock("@/hooks/use-trips", () => ({
    useTrips: () => ({
      data: items === null ? null : { items, total: items.length },
      isLoading,
      error: null,
      refetch: vi.fn(),
    }),
  }));
}

describe.sequential("RecentTrips", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.resetModules();
  });

  it("renders loading state correctly", async () => {
    await doMockTrips(null, true);
    const { RecentTrips } = await import("../recent-trips");
    renderWithProviders(<RecentTrips />);
    expect(screen.getByText("Recent Trips")).toBeInTheDocument();
    expect(screen.getByText("Your latest travel plans")).toBeInTheDocument();
    expect(document.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0);
  });

  it("renders empty state when no trips exist", async () => {
    await doMockTrips([]);
    const { RecentTrips } = await import("../recent-trips");
    renderWithProviders(<RecentTrips />);
    expect(screen.getByText("No recent trips yet.")).toBeInTheDocument();
    expect(screen.getByText("Create your first trip")).toBeInTheDocument();
  });

  it("renders trip cards for existing trips", async () => {
    await doMockTrips(mockTrips);
    const { RecentTrips } = await import("../recent-trips");
    renderWithProviders(<RecentTrips />);
    expect(screen.getByText("Tokyo Adventure")).toBeInTheDocument();
    expect(screen.getByText("European Tour")).toBeInTheDocument();
    expect(screen.getByText("Beach Getaway")).toBeInTheDocument();
  });

  it("displays trip details correctly", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2024-01-10T00:00:00Z"));
    await doMockTrips([mockTrips[0], mockTrips[1]]);
    const { RecentTrips } = await import("../recent-trips");
    const { container } = renderWithProviders(<RecentTrips />);
    const tokyoLink = within(container).getByRole("link", { name: /Tokyo Adventure/i });
    const scope = within(tokyoLink);
    expect(scope.getByText("Tokyo Adventure")).toBeInTheDocument();
    expect(scope.getByText("Tokyo")).toBeInTheDocument();
    expect(scope.getByText("7 days")).toBeInTheDocument();
    expect(scope.getByText(/upcoming|ongoing|completed/)).toBeInTheDocument();
    expect(scope.getByText("Exploring Japan's capital city")).toBeInTheDocument();
    vi.useRealTimers();
  });

  it("handles trips with multiple destinations", async () => {
    await doMockTrips([mockTrips[0], mockTrips[1]]);
    const { RecentTrips } = await import("../recent-trips");
    const { container } = renderWithProviders(<RecentTrips />);
    const europeanLink = within(container).getByRole("link", {
      name: /European Tour/i,
    });
    const scope = within(europeanLink);
    expect(scope.getByText("European Tour")).toBeInTheDocument();
    expect(scope.getByText("Paris (+1 more)")).toBeInTheDocument();
  });

  it("limits the number of trips displayed", async () => {
    await doMockTrips(mockTrips);
    const { RecentTrips } = await import("../recent-trips");
    renderWithProviders(<RecentTrips limit={2} />);
    expect(screen.getByText("European Tour")).toBeInTheDocument();
    expect(screen.getByText("Tokyo Adventure")).toBeInTheDocument();
    expect(screen.queryByText("Beach Getaway")).not.toBeInTheDocument();
  });

  it("sorts trips by updated date in descending order", async () => {
    await doMockTrips(mockTrips);
    const { RecentTrips } = await import("../recent-trips");
    renderWithProviders(<RecentTrips />);
    const tripCards = screen.getAllByRole("link");
    const tripTitles = tripCards.map((c) => c.textContent);
    expect(tripTitles[0]).toContain("European Tour");
  });

  it("navigates to trip details when card is clicked", async () => {
    await doMockTrips([mockTrips[0], mockTrips[1]]);
    userEvent.setup();
    const { RecentTrips } = await import("../recent-trips");
    const { container } = renderWithProviders(<RecentTrips />);
    const { getByRole } = within(container);
    const tripCard = getByRole("link", { name: /Tokyo Adventure/i });
    expect(tripCard).toHaveAttribute("href", "/dashboard/trips/trip-1");
  });

  it("handles showEmpty prop correctly", async () => {
    await doMockTrips([]);
    const { RecentTrips } = await import("../recent-trips");
    const { rerender } = renderWithProviders(<RecentTrips showEmpty={false} />);
    expect(screen.queryByText("Create your first trip")).not.toBeInTheDocument();
    expect(screen.getByText("No recent trips yet.")).toBeInTheDocument();
    rerender(<RecentTrips showEmpty={true} />);
    expect(screen.getByText("Create your first trip")).toBeInTheDocument();
  });

  it("calculates trip status correctly", async () => {
    const now = new Date();
    const pastTrip: Trip = {
      ...mockTrips[0],
      startDate: new Date(now.getTime() - 10 * 24 * 60 * 60 * 1000).toISOString(),
      endDate: new Date(now.getTime() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    };
    const ongoingTrip: Trip = {
      ...mockTrips[0],
      id: "ongoing-trip",
      startDate: new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000).toISOString(),
      endDate: new Date(now.getTime() + 3 * 24 * 60 * 60 * 1000).toISOString(),
    };
    await doMockTrips([pastTrip, ongoingTrip]);
    const { RecentTrips } = await import("../recent-trips");
    renderWithProviders(<RecentTrips />);
    expect(screen.getByText("completed")).toBeInTheDocument();
    expect(screen.getByText("ongoing")).toBeInTheDocument();
  });

  it("formats dates correctly", async () => {
    await doMockTrips([mockTrips[0]]);
    const { RecentTrips } = await import("../recent-trips");
    const { container } = renderWithProviders(<RecentTrips />);
    // Assert date substrings anywhere in the rendered card content
    expect(within(container).getByText(/Jun 15, 2024/)).toBeInTheDocument();
    expect(within(container).getByText(/Jun 22, 2024/)).toBeInTheDocument();
  });

  it("handles missing trip description gracefully", async () => {
    const tripWithoutDescription: Trip = { ...mockTrips[0], description: undefined };
    await doMockTrips([tripWithoutDescription]);
    const { RecentTrips } = await import("../recent-trips");
    const { container } = renderWithProviders(<RecentTrips />);
    // Ensure the description string is not present anywhere for this single-item case
    expect(within(container).getByText("Tokyo Adventure")).toBeInTheDocument();
    expect(
      within(container).queryByText("Exploring Japan's capital city")
    ).not.toBeInTheDocument();
  });
});
