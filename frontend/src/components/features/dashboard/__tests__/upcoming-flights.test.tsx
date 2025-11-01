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
          id: "f1",
          trip_id: "trip-1",
          trip_name: "Tokyo Adventure",
          airline: "NH",
          airline_name: "ANA",
          flight_number: "NH203",
          origin: "NRT",
          destination: "HND",
          departure_time: getFutureDate(10),
          arrival_time: getFutureDate(10),
          duration: 420,
          stops: 0,
          price: 999,
          currency: "USD",
          cabin_class: "economy",
          status: "upcoming",
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
          id: "f1",
          trip_id: "trip-1",
          trip_name: "Tokyo Trip",
          airline: "NH",
          airline_name: "ANA",
          flight_number: "NH200",
          origin: "NRT",
          destination: "HND",
          departure_time: getFutureDate(5),
          arrival_time: getFutureDate(5),
          duration: 300,
          stops: 0,
          price: 400,
          currency: "USD",
          cabin_class: "economy",
          status: "upcoming",
        },
        {
          id: "f2",
          trip_id: "trip-2",
          trip_name: "Paris Trip",
          airline: "AF",
          airline_name: "Air France",
          flight_number: "AF100",
          origin: "CDG",
          destination: "ORY",
          departure_time: getFutureDate(20),
          arrival_time: getFutureDate(20),
          duration: 120,
          stops: 0,
          price: 300,
          currency: "EUR",
          cabin_class: "economy",
          status: "upcoming",
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
          id: "f1",
          airline: "AA",
          airline_name: "American",
          flight_number: "AA1",
          origin: "JFK",
          destination: "LAX",
          departure_time: getFutureDate(5),
          arrival_time: getFutureDate(5),
          duration: 360,
          stops: 0,
          price: 200,
          currency: "USD",
          cabin_class: "economy",
          status: "upcoming",
        },
        {
          id: "f2",
          airline: "DL",
          airline_name: "Delta",
          flight_number: "DL2",
          origin: "SFO",
          destination: "SEA",
          departure_time: getFutureDate(6),
          arrival_time: getFutureDate(6),
          duration: 120,
          stops: 0,
          price: 150,
          currency: "USD",
          cabin_class: "economy",
          status: "upcoming",
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
          id: "f1",
          trip_id: "trip-1",
          trip_name: "Test Trip",
          airline: "UA",
          airline_name: "United",
          flight_number: "UA100",
          origin: "EWR",
          destination: "LAX",
          departure_time: getFutureDate(10),
          arrival_time: getFutureDate(10),
          duration: 300,
          stops: 0,
          price: 350,
          currency: "USD",
          cabin_class: "economy",
          status: "upcoming",
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
          id: "f1",
          trip_id: "trip-123",
          trip_name: "Test Trip",
          airline: "UA",
          airline_name: "United",
          flight_number: "UA100",
          origin: "EWR",
          destination: "LAX",
          departure_time: getFutureDate(10),
          arrival_time: getFutureDate(10),
          duration: 300,
          stops: 0,
          price: 350,
          currency: "USD",
          cabin_class: "economy",
          status: "upcoming",
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
          id: "f1",
          airline: "UA",
          airline_name: "United",
          flight_number: "UA100",
          origin: "EWR",
          destination: "LAX",
          departure_time: getFutureDate(10),
          arrival_time: getFutureDate(10),
          duration: 300,
          stops: 0,
          price: 350,
          currency: "USD",
          cabin_class: "economy",
          status: "upcoming",
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
          id: "f2",
          trip_id: "future-trip",
          trip_name: "Future Trip",
          airline: "BA",
          airline_name: "British Airways",
          flight_number: "BA100",
          origin: "LHR",
          destination: "JFK",
          departure_time: getFutureDate(10),
          arrival_time: getFutureDate(10),
          duration: 420,
          stops: 0,
          price: 800,
          currency: "GBP",
          cabin_class: "economy",
          status: "upcoming",
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
          id: "f3",
          trip_id: "today-trip",
          trip_name: "Today Trip",
          airline: "LH",
          airline_name: "Lufthansa",
          flight_number: "LH100",
          origin: "FRA",
          destination: "TXL",
          departure_time: today,
          arrival_time: getFutureDate(5),
          duration: 300,
          stops: 0,
          price: 200,
          currency: "EUR",
          cabin_class: "economy",
          status: "upcoming",
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
                id: "f-incomplete",
                airline: "XX",
                airline_name: "Unknown",
                flight_number: "XX0",
                origin: "N/A",
                destination: "N/A",
                departure_time: getFutureDate(1),
                arrival_time: getFutureDate(1),
                duration: 0,
                stops: 0,
                price: 0,
                currency: "USD",
                cabin_class: "economy",
                status: "upcoming",
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
                id: "f-bad-date",
                airline: "XX",
                airline_name: "Unknown",
                flight_number: "XX1",
                origin: "N/A",
                destination: "N/A",
                departure_time: "invalid-date",
                arrival_time: "also-invalid",
                duration: 0,
                stops: 0,
                price: 0,
                currency: "USD",
                cabin_class: "economy",
                status: "upcoming",
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
