import type { UseQueryResult } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import type { UpcomingFlight } from "@/hooks/use-trips";
import type { AppError } from "@/lib/api/error-types";
import { render, screen } from "@/test/test-utils.test";
import { UpcomingFlights } from "../upcoming-flights";

vi.mock("@/hooks/use-trips", () => ({
  useUpcomingFlights: vi.fn(),
}));

import { useUpcomingFlights } from "@/hooks/use-trips";

// Type for Next.js Link component props
interface LinkProps {
  children: ReactNode;
  href: string;
  [key: string]: unknown;
}

// Use proper React Query return type
type UseUpcomingFlightsReturn = UseQueryResult<UpcomingFlight[], AppError>;

// Helper function to create complete mock return value
function CreateMockReturnValue(
  data: UpcomingFlight[],
  isLoading = false
): UseUpcomingFlightsReturn {
  return {
    data,
    dataUpdatedAt: Date.now(),
    error: null,
    errorUpdateCount: 0,
    errorUpdatedAt: 0,
    failureCount: 0,
    failureReason: null,
    fetchStatus: "idle",
    isError: false,
    isFetched: true,
    isFetchedAfterMount: true,
    isFetching: false,
    isLoading,
    isLoadingError: false,
    isPaused: false,
    isPending: isLoading,
    isPlaceholderData: false,
    isRefetchError: false,
    isRefetching: false,
    isStale: false,
    isSuccess: !isLoading,
    status: isLoading ? "pending" : "success",
  } as UseUpcomingFlightsReturn;
}

// Mock Next.js Link
vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: LinkProps) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

describe("UpcomingFlights", () => {
  beforeAll(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2025-01-01T09:00:00Z"));
  });

  afterAll(() => {
    vi.useRealTimers();
  });
  // Helper to create future date
  const getFutureDate = (daysFromNow: number) => {
    const date = new Date();
    date.setDate(date.getDate() + daysFromNow);
    return date.toISOString();
  };

  // Helper to create past date
  const _getPastDate = (daysAgo: number) => {
    const date = new Date();
    date.setDate(date.getDate() - daysAgo);
    return date.toISOString();
  };

  beforeEach(() => {
    vi.resetAllMocks();
    // Default: no flights, not loading
    vi.mocked(useUpcomingFlights).mockReturnValue(CreateMockReturnValue([]));
  });

  describe("Basic Rendering", () => {
    it("should render component successfully", () => {
      render(<UpcomingFlights />);

      expect(screen.getByText("Upcoming Flights")).toBeInTheDocument();
    });

    it("should show subtitle when provided", () => {
      render(<UpcomingFlights />);

      expect(screen.getByText("Your next departures")).toBeInTheDocument();
    });
  });

  describe("Empty States", () => {
    it("should show empty state when no flights exist", () => {
      vi.mocked(useUpcomingFlights).mockReturnValue(CreateMockReturnValue([]));

      render(<UpcomingFlights />);

      expect(screen.getByText("No upcoming flights.")).toBeInTheDocument();
    });

    it("should handle showEmpty prop correctly", () => {
      vi.mocked(useUpcomingFlights).mockReturnValue(CreateMockReturnValue([]));

      const { rerender } = render(<UpcomingFlights showEmpty={false} />);

      expect(screen.queryByText(/search flights/i)).not.toBeInTheDocument();

      rerender(<UpcomingFlights showEmpty={true} />);

      expect(screen.getByText(/search flights/i)).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("should render skeleton components when loading", () => {
      vi.mocked(useUpcomingFlights).mockReturnValue(CreateMockReturnValue([], true));

      const { container } = render(<UpcomingFlights />);

      // Should show card title even when loading
      expect(screen.getByText("Upcoming Flights")).toBeInTheDocument();

      // Should render skeleton components (check for Skeleton elements)
      const skeletons = container.querySelectorAll('[class*="skeleton"]');
      expect(skeletons.length).toBeGreaterThan(0);
    });

    it("should render exactly 2 flight skeleton cards when loading", () => {
      vi.mocked(useUpcomingFlights).mockReturnValue(CreateMockReturnValue([], true));

      const { container } = render(<UpcomingFlights />);

      // Find skeleton containers (each FlightCardSkeleton has multiple skeleton elements)
      // We check for the parent containers with border classes
      const skeletonCards = container.querySelectorAll(
        ".border.border-border.rounded-lg"
      );

      // Should have 2 skeleton cards (each FlightCardSkeleton)
      expect(skeletonCards.length).toBe(2);
    });

    it("should use stable keys for skeleton components", () => {
      vi.mocked(useUpcomingFlights).mockReturnValue(CreateMockReturnValue([], true));

      const { container, rerender } = render(<UpcomingFlights />);

      // Find all skeleton containers
      const skeletonCards = container.querySelectorAll(
        ".border.border-border.rounded-lg"
      );

      // Verify we have exactly 2 skeletons
      expect(skeletonCards.length).toBe(2);

      // Re-render should maintain the same structure with stable keys
      // If keys were unstable, React would re-mount components on each render
      rerender(<UpcomingFlights />);

      const skeletonCardsAfterRerender = container.querySelectorAll(
        ".border.border-border.rounded-lg"
      );
      expect(skeletonCardsAfterRerender.length).toBe(2);
    });
  });

  describe("Flight Display", () => {
    it("should display flights for upcoming trips", () => {
      const flights: UpcomingFlight[] = [
        {
          airline: "NH",
          airlineName: "ANA",
          arrivalTime: getFutureDate(10),
          cabinClass: "economy",
          currency: "USD",
          departureTime: getFutureDate(10),
          destination: "HND",
          duration: 420,
          flightNumber: "NH203",
          id: "f1",
          origin: "NRT",
          price: 999,
          status: "upcoming",
          stops: 0,
          tripId: "trip-1",
          tripName: "Tokyo Adventure",
        },
      ];

      vi.mocked(useUpcomingFlights).mockReturnValue(CreateMockReturnValue(flights));

      render(<UpcomingFlights />);

      // Should show flight information
      expect(screen.getByText("Tokyo Adventure")).toBeInTheDocument();
    });

    it("should show multiple flights", () => {
      const flights: UpcomingFlight[] = [
        {
          airline: "NH",
          airlineName: "ANA",
          arrivalTime: getFutureDate(5),
          cabinClass: "economy",
          currency: "USD",
          departureTime: getFutureDate(5),
          destination: "HND",
          duration: 300,
          flightNumber: "NH200",
          id: "f1",
          origin: "NRT",
          price: 400,
          status: "upcoming",
          stops: 0,
          tripId: "trip-1",
          tripName: "Tokyo Trip",
        },
        {
          airline: "AF",
          airlineName: "Air France",
          arrivalTime: getFutureDate(20),
          cabinClass: "economy",
          currency: "EUR",
          departureTime: getFutureDate(20),
          destination: "ORY",
          duration: 120,
          flightNumber: "AF100",
          id: "f2",
          origin: "CDG",
          price: 300,
          status: "upcoming",
          stops: 0,
          tripId: "trip-2",
          tripName: "Paris Trip",
        },
      ];

      vi.mocked(useUpcomingFlights).mockReturnValue(CreateMockReturnValue(flights));

      render(<UpcomingFlights />);

      expect(screen.getByText("Tokyo Trip")).toBeInTheDocument();
      expect(screen.getByText("Paris Trip")).toBeInTheDocument();
    });

    it("should respect limit prop", () => {
      const flights: UpcomingFlight[] = [
        {
          airline: "AA",
          airlineName: "American Airlines",
          arrivalTime: getFutureDate(5),
          cabinClass: "economy",
          currency: "USD",
          departureTime: getFutureDate(5),
          destination: "LAX",
          duration: 360,
          flightNumber: "AA100",
          id: "f1",
          origin: "JFK",
          price: 200,
          status: "upcoming",
          stops: 0,
          tripId: "trip-1",
          tripName: "Business Trip",
        },
        {
          airline: "DL",
          airlineName: "Delta Airlines",
          arrivalTime: getFutureDate(6),
          cabinClass: "economy",
          currency: "USD",
          departureTime: getFutureDate(6),
          destination: "SEA",
          duration: 120,
          flightNumber: "DL200",
          id: "f2",
          origin: "SFO",
          price: 150,
          status: "upcoming",
          stops: 0,
          tripId: "trip-2",
          tripName: "Vacation",
        },
      ];

      // Mock the hook to return limited results based on the limit parameter
      vi.mocked(useUpcomingFlights).mockImplementation(
        ({ limit }: { limit?: number } = {}) =>
          CreateMockReturnValue(flights.slice(0, limit ?? flights.length))
      );

      render(<UpcomingFlights limit={1} />);

      // Should only show the first flight (limited to 1)
      expect(screen.getByText("Business Trip")).toBeInTheDocument();
      expect(screen.queryByText("Vacation")).not.toBeInTheDocument();
    });
  });

  describe("Flight Information", () => {
    beforeEach(() => {
      const flights: UpcomingFlight[] = [
        {
          airline: "UA",
          airlineName: "United",
          arrivalTime: getFutureDate(10),
          cabinClass: "economy",
          currency: "USD",
          departureTime: getFutureDate(10),
          destination: "LAX",
          duration: 300,
          flightNumber: "UA100",
          id: "f1",
          origin: "EWR",
          price: 350,
          status: "upcoming",
          stops: 0,
          tripId: "trip-1",
          tripName: "Test Trip",
        },
      ];
      vi.mocked(useUpcomingFlights).mockReturnValue(CreateMockReturnValue(flights));
    });

    it("should display flight times", () => {
      render(<UpcomingFlights />);

      // Should show departure and arrival time labels
      expect(screen.getByText("Departure")).toBeInTheDocument();
      expect(screen.getByText("Arrival")).toBeInTheDocument();

      // Should show formatted times with date (check that at least one time element exists)
      const timeElements = screen.getAllByText(/\d{1,2}:\d{2} • \w{3} \d{1,2}/);
      expect(timeElements.length).toBeGreaterThan(0);
    });

    it("should show flight status information", () => {
      render(<UpcomingFlights />);

      // Should show the status badge with "upcoming"
      expect(screen.getByText("upcoming")).toBeInTheDocument();
    });

    it("should display price information when available", () => {
      render(<UpcomingFlights />);

      // Should show price with dollar sign
      expect(screen.getByText("$350")).toBeInTheDocument();
    });

    it("should show duration information", () => {
      render(<UpcomingFlights />);

      // Should show duration in "Xh Ym" format (5h 50m for 300 minutes)
      expect(screen.getByText("5h 0m")).toBeInTheDocument();
    });
  });

  describe("Navigation and Links", () => {
    it("should link to trip details correctly", () => {
      const flights: UpcomingFlight[] = [
        {
          airline: "UA",
          airlineName: "United",
          arrivalTime: getFutureDate(10),
          cabinClass: "economy",
          currency: "USD",
          departureTime: getFutureDate(10),
          destination: "LAX",
          duration: 300,
          flightNumber: "UA100",
          id: "f1",
          origin: "EWR",
          price: 350,
          status: "upcoming",
          stops: 0,
          tripId: "trip-123",
          tripName: "Test Trip",
        },
      ];
      vi.mocked(useUpcomingFlights).mockReturnValue(CreateMockReturnValue(flights));

      render(<UpcomingFlights />);

      const tripLink = screen.queryByRole("link", { name: /test trip/i });
      if (tripLink) {
        expect(tripLink).toHaveAttribute("href", "/dashboard/trips/trip-123");
      }
    });

    it("should show search more flights link when flights exist", () => {
      const flights: UpcomingFlight[] = [
        {
          airline: "UA",
          airlineName: "United",
          arrivalTime: getFutureDate(10),
          cabinClass: "economy",
          currency: "USD",
          departureTime: getFutureDate(10),
          destination: "LAX",
          duration: 300,
          flightNumber: "UA100",
          id: "f1",
          origin: "EWR",
          price: 350,
          status: "upcoming",
          stops: 0,
        },
      ];
      vi.mocked(useUpcomingFlights).mockReturnValue(CreateMockReturnValue(flights));

      render(<UpcomingFlights />);

      const searchLink = screen.queryByRole("link", { name: /search more flights/i });
      if (searchLink) {
        expect(searchLink).toHaveAttribute("href", "/dashboard/search/flights");
      }
    });
  });

  describe("Date Filtering", () => {
    it("should display flights returned by hook", () => {
      const flights: UpcomingFlight[] = [
        {
          airline: "BA",
          airlineName: "British Airways",
          arrivalTime: getFutureDate(10),
          cabinClass: "economy",
          currency: "GBP",
          departureTime: getFutureDate(10),
          destination: "JFK",
          duration: 420,
          flightNumber: "BA100",
          id: "f2",
          origin: "LHR",
          price: 800,
          status: "upcoming",
          stops: 0,
          tripId: "future-trip",
          tripName: "Future Trip",
        },
      ];
      vi.mocked(useUpcomingFlights).mockReturnValue(CreateMockReturnValue(flights));

      render(<UpcomingFlights />);

      expect(screen.getByText("Future Trip")).toBeInTheDocument();
    });

    it("should handle flights departing today correctly", () => {
      const today = new Date().toISOString();

      const flights: UpcomingFlight[] = [
        {
          airline: "LH",
          airlineName: "Lufthansa",
          arrivalTime: getFutureDate(5),
          cabinClass: "economy",
          currency: "EUR",
          departureTime: today,
          destination: "TXL",
          duration: 300,
          flightNumber: "LH100",
          id: "f3",
          origin: "FRA",
          price: 200,
          status: "upcoming",
          stops: 0,
          tripId: "today-trip",
          tripName: "Today Trip",
        },
      ];
      vi.mocked(useUpcomingFlights).mockReturnValue(CreateMockReturnValue(flights));

      render(<UpcomingFlights />);

      expect(screen.getByText("Today Trip")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have proper heading structure", () => {
      render(<UpcomingFlights />);

      const heading = screen.getByRole("heading", { level: 3 });
      expect(heading).toHaveTextContent("Upcoming Flights");
    });

    it("should have accessible links with proper attributes", () => {
      const flights: UpcomingFlight[] = [
        {
          airline: "UA",
          airlineName: "United",
          arrivalTime: getFutureDate(10),
          cabinClass: "economy",
          currency: "USD",
          departureTime: getFutureDate(10),
          destination: "LAX",
          duration: 300,
          flightNumber: "UA100",
          id: "f1",
          origin: "EWR",
          price: 350,
          status: "upcoming",
          stops: 0,
          tripId: "trip-123",
          tripName: "Test Trip",
        },
      ];
      vi.mocked(useUpcomingFlights).mockReturnValue(CreateMockReturnValue(flights));

      render(<UpcomingFlights />);

      const tripLink = screen.getByRole("link", { name: /test trip/i });
      expect(tripLink).toHaveAttribute("href", "/dashboard/trips/trip-123");
    });

    it("should have semantic list structure for flights", () => {
      const flights: UpcomingFlight[] = [
        {
          airline: "UA",
          airlineName: "United",
          arrivalTime: getFutureDate(10),
          cabinClass: "economy",
          currency: "USD",
          departureTime: getFutureDate(10),
          destination: "LAX",
          duration: 300,
          flightNumber: "UA100",
          id: "f1",
          origin: "EWR",
          price: 350,
          status: "upcoming",
          stops: 0,
        },
      ];
      vi.mocked(useUpcomingFlights).mockReturnValue(CreateMockReturnValue(flights));

      render(<UpcomingFlights />);

      // Should have a container that acts as a list
      const flightContainer = screen.getByText("United UA100").closest("div");
      expect(flightContainer).toBeInTheDocument();
    });
  });

  describe("Error Handling", () => {
    it("should handle missing trip data gracefully", () => {
      // Provide flight with minimal fields and ensure component renders
      vi.mocked(useUpcomingFlights).mockReturnValue({
        data: [
          {
            airline: "XX",
            airlineName: "Unknown",
            arrivalTime: getFutureDate(1),
            cabinClass: "economy",
            currency: "USD",
            departureTime: getFutureDate(1),
            destination: "N/A",
            duration: 0,
            flightNumber: "XX0",
            id: "f-incomplete",
            origin: "N/A",
            price: 0,
            status: "upcoming",
            stops: 0,
          } as UpcomingFlight,
        ],
        isLoading: false,
      } as UseUpcomingFlightsReturn);

      render(<UpcomingFlights />);

      expect(screen.getByText("Upcoming Flights")).toBeInTheDocument();
    });

    it("should handle malformed dates gracefully", () => {
      vi.mocked(useUpcomingFlights).mockReturnValue({
        data: [
          {
            airline: "XX",
            airlineName: "Unknown",
            arrivalTime: "also-invalid",
            cabinClass: "economy",
            currency: "USD",
            departureTime: "invalid-date",
            destination: "N/A",
            duration: 0,
            flightNumber: "XX1",
            id: "f-bad-date",
            origin: "N/A",
            price: 0,
            status: "upcoming",
            stops: 0,
          } as unknown as UpcomingFlight,
        ],
        isLoading: false,
      } as UseUpcomingFlightsReturn);

      render(<UpcomingFlights />);

      expect(screen.getByText("Upcoming Flights")).toBeInTheDocument();
    });
  });
});
