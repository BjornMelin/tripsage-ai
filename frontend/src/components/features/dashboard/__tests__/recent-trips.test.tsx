/** @vitest-environment jsdom */

import { screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/test-utils";
import { createFakeTimersContext } from "@/test/utils/with-fake-timers";

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

// Hoisted state for controlling useTrips mock behavior
const TripsState = vi.hoisted(() => ({
  isLoading: false,
  items: null as Array<Record<string, unknown>> | null,
}));

vi.mock("@/hooks/use-trips", () => ({
  useTrips: () => ({
    data: TripsState.items,
    error: null,
    isConnected: true,
    isLoading: TripsState.isLoading,
    realtimeStatus: {
      errors: [],
      isConnected: true,
    },
    refetch: vi.fn(),
  }),
}));

// Static import after mocks are set up - single module load
import { RecentTrips } from "../recent-trips";

const MockTrips: Array<Record<string, unknown>> = [
  {
    budget: 3000,
    createdAt: "2024-01-15T00:00:00Z",
    currency: "USD",
    description: "Exploring Japan's capital city",
    destinations: [{ country: "Japan", id: "dest-1", name: "Tokyo" }],
    endDate: "2024-06-22T00:00:00Z",
    id: "trip-1",
    startDate: "2024-06-15T00:00:00Z",
    title: "Tokyo Adventure",
    updatedAt: "2024-01-16T00:00:00Z",
    visibility: "private",
  },
  {
    budget: 5000,
    createdAt: "2024-01-10T00:00:00Z",
    currency: "USD",
    description: "Multi-city European adventure",
    destinations: [
      { country: "France", id: "dest-2", name: "Paris" },
      { country: "Italy", id: "dest-3", name: "Rome" },
    ],
    endDate: "2024-08-15T00:00:00Z",
    id: "trip-2",
    startDate: "2024-08-01T00:00:00Z",
    title: "European Tour",
    updatedAt: "2024-01-20T00:00:00Z",
    visibility: "public",
  },
  {
    createdAt: "2024-01-05T00:00:00Z",
    destinations: [],
    id: "trip-3",
    title: "Beach Getaway",
    updatedAt: "2024-01-05T00:00:00Z",
    visibility: "private",
  },
];

// biome-ignore lint/style/useNamingConvention: Test helper utility
function setTrips(items: Array<Record<string, unknown>> | null, isLoading = false) {
  TripsState.items = items;
  TripsState.isLoading = isLoading;
}

describe("RecentTrips", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setTrips(null, false);
  });

  it("renders loading state correctly", () => {
    setTrips(null, true);
    renderWithProviders(<RecentTrips />);
    expect(screen.getByText("Recent Trips")).toBeInTheDocument();
    expect(screen.getByText("Your latest travel plans")).toBeInTheDocument();
    expect(screen.getAllByTestId("trip-skeleton").length).toBeGreaterThan(0);
  });

  it("renders empty state when no trips exist", () => {
    setTrips([]);
    renderWithProviders(<RecentTrips />);
    const emptyMessages = screen.getAllByText("No recent trips yet.");
    expect(emptyMessages.length).toBeGreaterThan(0);
    expect(emptyMessages[0]).toBeInTheDocument();
    const createLinks = screen.getAllByText("Create your first trip");
    expect(createLinks.length).toBeGreaterThan(0);
    expect(createLinks[0]).toBeInTheDocument();
  });

  it("renders trip cards for existing trips", () => {
    setTrips(MockTrips);
    renderWithProviders(<RecentTrips />);
    expect(screen.getByText("Tokyo Adventure")).toBeInTheDocument();
    expect(screen.getByText("European Tour")).toBeInTheDocument();
    expect(screen.getByText("Beach Getaway")).toBeInTheDocument();
  });

  describe("with fixed system time", () => {
    const timers = createFakeTimersContext();

    beforeEach(() => {
      timers.setup();
      vi.setSystemTime(new Date("2024-01-10T00:00:00Z"));
    });

    afterEach(() => {
      timers.teardown();
    });

    it("displays trip details correctly", () => {
      setTrips([MockTrips[0], MockTrips[1]]);
      const { container } = renderWithProviders(<RecentTrips />);
      const tokyoLink = within(container).getByRole("link", {
        name: /Tokyo Adventure/i,
      });
      const scope = within(tokyoLink);
      expect(scope.getByText("Tokyo Adventure")).toBeInTheDocument();
      expect(scope.getByText("Tokyo")).toBeInTheDocument();
      expect(scope.getByText("7 days")).toBeInTheDocument();
      expect(scope.getByTestId("trip-status")).toHaveTextContent("upcoming");
      expect(scope.getByText("Exploring Japan's capital city")).toBeInTheDocument();
    });
  });

  it("handles trips with multiple destinations", () => {
    setTrips([MockTrips[0], MockTrips[1]]);
    const { container } = renderWithProviders(<RecentTrips />);
    const europeanLink = within(container).getByRole("link", {
      name: /European Tour/i,
    });
    const scope = within(europeanLink);
    expect(scope.getByText("European Tour")).toBeInTheDocument();
    expect(scope.getByText("Paris (+1 more)")).toBeInTheDocument();
  });

  it("limits the number of trips displayed", () => {
    setTrips(MockTrips);
    renderWithProviders(<RecentTrips limit={2} />);
    expect(screen.getByText("European Tour")).toBeInTheDocument();
    expect(screen.getByText("Tokyo Adventure")).toBeInTheDocument();
    expect(screen.queryByText("Beach Getaway")).not.toBeInTheDocument();
  });

  it("sorts trips by updated date in descending order", () => {
    setTrips(MockTrips);
    renderWithProviders(<RecentTrips />);
    const tripCards = screen.getAllByRole("link");
    const tripTitles = tripCards.map((c) => c.textContent);
    expect(tripTitles[0]).toContain("European Tour");
  });

  it("navigates to trip details when card is clicked", () => {
    setTrips([MockTrips[0], MockTrips[1]]);
    const { container } = renderWithProviders(<RecentTrips />);
    const { getByRole } = within(container);
    const tripCard = getByRole("link", { name: /Tokyo Adventure/i });
    expect(tripCard).toHaveAttribute("href", "/dashboard/trips/trip-1");
  });

  it("handles showEmpty prop correctly", () => {
    setTrips([]);
    const { rerender } = renderWithProviders(<RecentTrips showEmpty={false} />);
    expect(screen.queryByText("Create your first trip")).not.toBeInTheDocument();
    expect(screen.getByText("No recent trips yet.")).toBeInTheDocument();
    rerender(<RecentTrips showEmpty={true} />);
    expect(screen.getByText("Create your first trip")).toBeInTheDocument();
  });

  it("calculates trip status correctly", () => {
    const now = new Date();
    const pastTrip: Record<string, unknown> = {
      ...MockTrips[0],
      endDate: new Date(now.getTime() - 5 * 24 * 60 * 60 * 1000).toISOString(),
      startDate: new Date(now.getTime() - 10 * 24 * 60 * 60 * 1000).toISOString(),
    };
    const ongoingTrip: Record<string, unknown> = {
      ...MockTrips[0],
      endDate: new Date(now.getTime() + 3 * 24 * 60 * 60 * 1000).toISOString(),
      id: "ongoing-trip",
      startDate: new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    };
    setTrips([pastTrip, ongoingTrip]);
    renderWithProviders(<RecentTrips />);
    expect(screen.getByText("completed")).toBeInTheDocument();
    expect(screen.getByText("ongoing")).toBeInTheDocument();
  });

  it("formats dates correctly", () => {
    setTrips([MockTrips[0]]);
    const { container } = renderWithProviders(<RecentTrips limit={1} />);
    // Assert US short month format regardless of specific dates present
    const shortDatePattern = /[A-Z][a-z]{2} \d{1,2}, \d{4}/;
    expect(within(container).getAllByText(shortDatePattern).length).toBeGreaterThan(0);
  });

  it("handles missing trip description gracefully", () => {
    const tripWithoutDescription: Record<string, unknown> = {
      ...MockTrips[0],
      description: undefined,
    };
    setTrips([tripWithoutDescription]);
    const { container } = renderWithProviders(<RecentTrips limit={1} />);
    // Assert that the known description text does not render when missing
    expect(
      within(container).queryByText("Exploring Japan's capital city")
    ).not.toBeInTheDocument();
  });
});
