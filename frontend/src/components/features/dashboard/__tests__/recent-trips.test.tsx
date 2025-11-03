/**
 * @fileoverview Stable tests for RecentTrips aligned with current UI.
 * Uses per-test module resets and doMock to avoid cross-test interference.
 */
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/test-utils";

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    // eslint-disable-next-line jsx-a11y/anchor-is-valid
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

const MOCK_TRIPS: Array<Record<string, unknown>> = [
  {
    budget: 3000,
    created_at: "2024-01-15T00:00:00Z",
    currency: "USD",
    description: "Exploring Japan's capital city",
    destinations: [{ country: "Japan", id: "dest-1", name: "Tokyo" }],
    endDate: "2024-06-22T00:00:00Z",
    id: "trip-1",
    isPublic: false,
    name: "Tokyo Adventure",
    startDate: "2024-06-15T00:00:00Z",
    updated_at: "2024-01-16T00:00:00Z",
  },
  {
    budget: 5000,
    created_at: "2024-01-10T00:00:00Z",
    currency: "USD",
    description: "Multi-city European adventure",
    destinations: [
      { country: "France", id: "dest-2", name: "Paris" },
      { country: "Italy", id: "dest-3", name: "Rome" },
    ],
    endDate: "2024-08-15T00:00:00Z",
    id: "trip-2",
    isPublic: true,
    name: "European Tour",
    startDate: "2024-08-01T00:00:00Z",
    updatedAt: "2024-01-20T00:00:00Z",
  },
  {
    createdAt: "2024-01-05T00:00:00Z",
    destinations: [],
    id: "trip-3",
    isPublic: false,
    name: "Beach Getaway",
    updatedAt: "2024-01-05T00:00:00Z",
  },
];

function doMockTrips(items: Array<Record<string, unknown>> | null, isLoading = false) {
  vi.resetModules();
  vi.doMock("@/hooks/use-trips", () => ({
    useTrips: () => ({
      data: items === null ? null : { items, total: items.length },
      error: null,
      isLoading,
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
    await doMockTrips(MOCK_TRIPS);
    const { RecentTrips } = await import("../recent-trips");
    renderWithProviders(<RecentTrips />);
    expect(screen.getByText("Tokyo Adventure")).toBeInTheDocument();
    expect(screen.getByText("European Tour")).toBeInTheDocument();
    expect(screen.getByText("Beach Getaway")).toBeInTheDocument();
  });

  it("displays trip details correctly", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2024-01-10T00:00:00Z"));
    await doMockTrips([MOCK_TRIPS[0], MOCK_TRIPS[1]]);
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
    await doMockTrips([MOCK_TRIPS[0], MOCK_TRIPS[1]]);
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
    await doMockTrips(MOCK_TRIPS);
    const { RecentTrips } = await import("../recent-trips");
    renderWithProviders(<RecentTrips limit={2} />);
    expect(screen.getByText("European Tour")).toBeInTheDocument();
    expect(screen.getByText("Tokyo Adventure")).toBeInTheDocument();
    expect(screen.queryByText("Beach Getaway")).not.toBeInTheDocument();
  });

  it("sorts trips by updated date in descending order", async () => {
    await doMockTrips(MOCK_TRIPS);
    const { RecentTrips } = await import("../recent-trips");
    renderWithProviders(<RecentTrips />);
    const tripCards = screen.getAllByRole("link");
    const tripTitles = tripCards.map((c) => c.textContent);
    expect(tripTitles[0]).toContain("European Tour");
  });

  it("navigates to trip details when card is clicked", async () => {
    await doMockTrips([MOCK_TRIPS[0], MOCK_TRIPS[1]]);
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
    const pastTrip: Record<string, unknown> = {
      ...MOCK_TRIPS[0],
      endDate: new Date(now.getTime() - 5 * 24 * 60 * 60 * 1000).toISOString(),
      startDate: new Date(now.getTime() - 10 * 24 * 60 * 60 * 1000).toISOString(),
    };
    const ongoingTrip: Record<string, unknown> = {
      ...MOCK_TRIPS[0],
      endDate: new Date(now.getTime() + 3 * 24 * 60 * 60 * 1000).toISOString(),
      id: "ongoing-trip",
      startDate: new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    };
    await doMockTrips([pastTrip, ongoingTrip]);
    const { RecentTrips } = await import("../recent-trips");
    renderWithProviders(<RecentTrips />);
    expect(screen.getByText("completed")).toBeInTheDocument();
    expect(screen.getByText("ongoing")).toBeInTheDocument();
  });

  it("formats dates correctly", async () => {
    await doMockTrips([MOCK_TRIPS[0]]);
    const { RecentTrips } = await import("../recent-trips");
    const { container } = renderWithProviders(<RecentTrips limit={1} />);
    // Assert US short month format regardless of specific dates present
    const shortDatePattern = /[A-Z][a-z]{2} \d{1,2}, \d{4}/;
    expect(within(container).getAllByText(shortDatePattern).length).toBeGreaterThan(0);
  });

  it("handles missing trip description gracefully", async () => {
    const tripWithoutDescription: Record<string, unknown> = {
      ...MOCK_TRIPS[0],
      description: undefined,
    };
    await doMockTrips([tripWithoutDescription]);
    const { RecentTrips } = await import("../recent-trips");
    const { container } = renderWithProviders(<RecentTrips limit={1} />);
    // Assert that the known description text does not render when missing
    expect(
      within(container).queryByText("Exploring Japan's capital city")
    ).not.toBeInTheDocument();
  });
});
