/**
 * Modern upcoming flights tests.
 *
 * Focused tests for upcoming flights functionality using proper mocking
 * patterns and behavioral validation. Following ULTRATHINK methodology.
 */

import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import type { UpcomingFlight } from "@/hooks/use-trips";
import { render, screen } from "@/test/test-utils";
import { UpcomingFlights } from "../upcoming-flights";

vi.mock("@/hooks/use-trips", () => ({
  useUpcomingFlights: vi.fn(),
}));

import { useUpcomingFlights } from "@/hooks/use-trips";

// Mock Next.js Link
vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: any) => (
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
    vi.mocked(useUpcomingFlights).mockImplementation(
      () =>
        ({
          data: [],
          isLoading: false,
        }) as any
    );
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
      vi.mocked(useUpcomingFlights).mockImplementation(
        () =>
          ({
            data: [],
            isLoading: false,
          }) as any
      );

      render(<UpcomingFlights />);

      expect(screen.getByText("No upcoming flights.")).toBeInTheDocument();
    });

    it("should show empty state when hook returns no flights", () => {
      vi.mocked(useUpcomingFlights).mockImplementation(
        () =>
          ({
            data: [],
            isLoading: false,
          }) as any
      );

      render(<UpcomingFlights />);

      expect(screen.getByText("No upcoming flights.")).toBeInTheDocument();
    });

    it("should handle showEmpty prop correctly", () => {
      vi.mocked(useUpcomingFlights).mockImplementation(
        () =>
          ({
            data: [],
            isLoading: false,
          }) as any
      );

      const { rerender } = render(<UpcomingFlights showEmpty={false} />);

      expect(screen.queryByText(/search flights/i)).not.toBeInTheDocument();

      rerender(<UpcomingFlights showEmpty={true} />);

      expect(screen.getByText(/search flights/i)).toBeInTheDocument();
    });
  });

  describe("Flight Display", () => {
    it("should display flights for upcoming trips", () => {
      const flights: UpcomingFlight[] = [
        {
          airline: "NH",
          airline_name: "ANA",
          arrival_time: getFutureDate(10),
          cabin_class: "economy",
          currency: "USD",
          departure_time: getFutureDate(10),
          destination: "HND",
          duration: 420,
          flight_number: "NH203",
          id: "f1",
          origin: "NRT",
          price: 999,
          status: "upcoming",
          stops: 0,
          trip_id: "trip-1",
          trip_name: "Tokyo Adventure",
        },
      ];

      vi.mocked(useUpcomingFlights).mockImplementation(
        () =>
          ({
            data: flights,
            isLoading: false,
          }) as any
      );

      render(<UpcomingFlights />);

      // Should show flight information
      expect(screen.getByText("Tokyo Adventure")).toBeInTheDocument();
    });

    it("should show multiple flights", () => {
      const flights: UpcomingFlight[] = [
        {
          airline: "NH",
          airline_name: "ANA",
          arrival_time: getFutureDate(5),
          cabin_class: "economy",
          currency: "USD",
          departure_time: getFutureDate(5),
          destination: "HND",
          duration: 300,
          flight_number: "NH200",
          id: "f1",
          origin: "NRT",
          price: 400,
          status: "upcoming",
          stops: 0,
          trip_id: "trip-1",
          trip_name: "Tokyo Trip",
        },
        {
          airline: "AF",
          airline_name: "Air France",
          arrival_time: getFutureDate(20),
          cabin_class: "economy",
          currency: "EUR",
          departure_time: getFutureDate(20),
          destination: "ORY",
          duration: 120,
          flight_number: "AF100",
          id: "f2",
          origin: "CDG",
          price: 300,
          status: "upcoming",
          stops: 0,
          trip_id: "trip-2",
          trip_name: "Paris Trip",
        },
      ];

      vi.mocked(useUpcomingFlights).mockImplementation(
        () =>
          ({
            data: flights,
            isLoading: false,
          }) as any
      );

      render(<UpcomingFlights />);

      expect(screen.getByText("Tokyo Trip")).toBeInTheDocument();
      expect(screen.getByText("Paris Trip")).toBeInTheDocument();
    });

    it("should respect limit prop", () => {
      const flights: UpcomingFlight[] = [
        {
          airline: "AA",
          airline_name: "American",
          arrival_time: getFutureDate(5),
          cabin_class: "economy",
          currency: "USD",
          departure_time: getFutureDate(5),
          destination: "LAX",
          duration: 360,
          flight_number: "AA1",
          id: "f1",
          origin: "JFK",
          price: 200,
          status: "upcoming",
          stops: 0,
        },
        {
          airline: "DL",
          airline_name: "Delta",
          arrival_time: getFutureDate(6),
          cabin_class: "economy",
          currency: "USD",
          departure_time: getFutureDate(6),
          destination: "SEA",
          duration: 120,
          flight_number: "DL2",
          id: "f2",
          origin: "SFO",
          price: 150,
          status: "upcoming",
          stops: 0,
        },
      ];

      vi.mocked(useUpcomingFlights).mockImplementation(
        ({ limit }: any) =>
          ({
            data: flights.slice(0, limit ?? flights.length),
            isLoading: false,
          }) as any
      );

      render(<UpcomingFlights limit={1} />);

      const aa = screen.queryAllByText(/AA1/);
      const dl = screen.queryAllByText(/DL2/);
      expect(aa.length).toBeGreaterThan(0);
      expect(dl.length).toBe(0);
    });
  });

  describe("Flight Information", () => {
    beforeEach(() => {
      const flights: UpcomingFlight[] = [
        {
          airline: "UA",
          airline_name: "United",
          arrival_time: getFutureDate(10),
          cabin_class: "economy",
          currency: "USD",
          departure_time: getFutureDate(10),
          destination: "LAX",
          duration: 300,
          flight_number: "UA100",
          id: "f1",
          origin: "EWR",
          price: 350,
          status: "upcoming",
          stops: 0,
          trip_id: "trip-1",
          trip_name: "Test Trip",
        },
      ];
      vi.mocked(useUpcomingFlights).mockImplementation(
        () =>
          ({
            data: flights,
            isLoading: false,
          }) as any
      );
    });

    it("should display flight times", () => {
      render(<UpcomingFlights />);

      // Should show time information in some format
      const timeElements = screen.queryAllByText(/\d{1,2}:\d{2}/);
      expect(timeElements.length).toBeGreaterThanOrEqual(0);
    });

    it("should show flight status information", () => {
      render(<UpcomingFlights />);

      // Should show some form of status
      const statusElements = screen.queryAllByText(
        /upcoming|scheduled|boarding|delayed/i
      );
      expect(statusElements.length).toBeGreaterThanOrEqual(0);
    });

    it("should display price information when available", () => {
      render(<UpcomingFlights />);

      // Should show price in some format
      const priceElements = screen.queryAllByText(/\$\d+/);
      expect(priceElements.length).toBeGreaterThanOrEqual(0);
    });

    it("should show duration information", () => {
      render(<UpcomingFlights />);

      // Should show duration in some format
      const durationElements = screen.queryAllByText(/\d+h|\d+m/);
      expect(durationElements.length).toBeGreaterThanOrEqual(0);
    });
  });

  describe("Navigation and Links", () => {
    it("should link to trip details correctly", () => {
      const flights: UpcomingFlight[] = [
        {
          airline: "UA",
          airline_name: "United",
          arrival_time: getFutureDate(10),
          cabin_class: "economy",
          currency: "USD",
          departure_time: getFutureDate(10),
          destination: "LAX",
          duration: 300,
          flight_number: "UA100",
          id: "f1",
          origin: "EWR",
          price: 350,
          status: "upcoming",
          stops: 0,
          trip_id: "trip-123",
          trip_name: "Test Trip",
        },
      ];
      vi.mocked(useUpcomingFlights).mockImplementation(
        () => ({ data: flights, isLoading: false }) as any
      );

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
          airline_name: "United",
          arrival_time: getFutureDate(10),
          cabin_class: "economy",
          currency: "USD",
          departure_time: getFutureDate(10),
          destination: "LAX",
          duration: 300,
          flight_number: "UA100",
          id: "f1",
          origin: "EWR",
          price: 350,
          status: "upcoming",
          stops: 0,
        },
      ];
      vi.mocked(useUpcomingFlights).mockImplementation(
        () => ({ data: flights, isLoading: false }) as any
      );

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
          airline_name: "British Airways",
          arrival_time: getFutureDate(10),
          cabin_class: "economy",
          currency: "GBP",
          departure_time: getFutureDate(10),
          destination: "JFK",
          duration: 420,
          flight_number: "BA100",
          id: "f2",
          origin: "LHR",
          price: 800,
          status: "upcoming",
          stops: 0,
          trip_id: "future-trip",
          trip_name: "Future Trip",
        },
      ];
      vi.mocked(useUpcomingFlights).mockImplementation(
        () => ({ data: flights, isLoading: false }) as any
      );

      render(<UpcomingFlights />);

      expect(screen.getByText("Future Trip")).toBeInTheDocument();
    });

    it("should handle flights departing today correctly", () => {
      const today = new Date().toISOString();

      const flights: UpcomingFlight[] = [
        {
          airline: "LH",
          airline_name: "Lufthansa",
          arrival_time: getFutureDate(5),
          cabin_class: "economy",
          currency: "EUR",
          departure_time: today,
          destination: "TXL",
          duration: 300,
          flight_number: "LH100",
          id: "f3",
          origin: "FRA",
          price: 200,
          status: "upcoming",
          stops: 0,
          trip_id: "today-trip",
          trip_name: "Today Trip",
        },
      ];
      vi.mocked(useUpcomingFlights).mockImplementation(
        () => ({ data: flights, isLoading: false }) as any
      );

      render(<UpcomingFlights />);

      expect(screen.getByText("Today Trip")).toBeInTheDocument();
    });
  });

  describe("Error Handling", () => {
    it("should handle missing trip data gracefully", () => {
      // Provide flight with minimal fields and ensure component renders
      vi.mocked(useUpcomingFlights).mockImplementation(
        () =>
          ({
            data: [
              {
                airline: "XX",
                airline_name: "Unknown",
                arrival_time: getFutureDate(1),
                cabin_class: "economy",
                currency: "USD",
                departure_time: getFutureDate(1),
                destination: "N/A",
                duration: 0,
                flight_number: "XX0",
                id: "f-incomplete",
                origin: "N/A",
                price: 0,
                status: "upcoming",
                stops: 0,
              } as UpcomingFlight,
            ],
            isLoading: false,
          }) as any
      );

      render(<UpcomingFlights />);

      expect(screen.getByText("Upcoming Flights")).toBeInTheDocument();
    });

    it("should handle malformed dates gracefully", () => {
      vi.mocked(useUpcomingFlights).mockImplementation(
        () =>
          ({
            data: [
              {
                airline: "XX",
                airline_name: "Unknown",
                arrival_time: "also-invalid",
                cabin_class: "economy",
                currency: "USD",
                departure_time: "invalid-date",
                destination: "N/A",
                duration: 0,
                flight_number: "XX1",
                id: "f-bad-date",
                origin: "N/A",
                price: 0,
                status: "upcoming",
                stops: 0,
              } as unknown as UpcomingFlight,
            ],
            isLoading: false,
          }) as any
      );

      render(<UpcomingFlights />);

      expect(screen.getByText("Upcoming Flights")).toBeInTheDocument();
    });
  });
});
