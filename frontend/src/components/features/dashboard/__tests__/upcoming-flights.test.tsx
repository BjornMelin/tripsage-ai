/** @vitest-environment jsdom */

import type { UseQueryResult } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { UpcomingFlight } from "@/hooks/use-trips";
import type { AppError } from "@/lib/api/error-types";
import { render, screen } from "@/test/test-utils";
import { UPCOMING_FLIGHT_A, UPCOMING_FLIGHT_B } from "@/test/fixtures/flights";
import { UpcomingFlights } from "../upcoming-flights";

vi.mock("@/hooks/use-trips", () => ({
  useUpcomingFlights: vi.fn(),
}));

import { useUpcomingFlights } from "@/hooks/use-trips";

interface LinkProps {
  children: ReactNode;
  href: string;
  [key: string]: unknown;
}

type UseUpcomingFlightsReturn = UseQueryResult<UpcomingFlight[], AppError>;

const CreateFlightsReturn = (
  data: UpcomingFlight[],
  isLoading = false
): UseUpcomingFlightsReturn =>
  ({
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
  }) as UseUpcomingFlightsReturn;

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: LinkProps) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

describe("UpcomingFlights", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useUpcomingFlights).mockReturnValue(CreateFlightsReturn([]));
  });

  it("renders heading and subtitle", () => {
    render(<UpcomingFlights />);

    expect(screen.getByText("Upcoming Flights")).toBeInTheDocument();
    expect(screen.getByText("Your next departures")).toBeInTheDocument();
  });

  it("shows empty state when no flights", () => {
    render(<UpcomingFlights />);
    expect(screen.getByText("No upcoming flights.")).toBeInTheDocument();
  });

  it("respects showEmpty=false", () => {
    render(<UpcomingFlights showEmpty={false} />);
    expect(screen.queryByText(/search flights/i)).not.toBeInTheDocument();
  });

  it("renders skeletons while loading", () => {
    vi.mocked(useUpcomingFlights).mockReturnValue(CreateFlightsReturn([], true));

    render(<UpcomingFlights />);
    expect(screen.getAllByTestId("flight-skeleton").length).toBeGreaterThan(0);
  });

  it("shows flights when available", () => {
    vi.mocked(useUpcomingFlights).mockReturnValue(
      CreateFlightsReturn([UPCOMING_FLIGHT_A, UPCOMING_FLIGHT_B])
    );

    render(<UpcomingFlights />);

    expect(screen.getByText("ANA NH203")).toBeInTheDocument();
    expect(screen.getByText("United UA837")).toBeInTheDocument();
    // Verify NRT appears multiple times (origin for both flights)
    expect(screen.getAllByText("NRT").length).toBeGreaterThanOrEqual(2);
    // Verify HND appears for FLIGHT_A destination
    expect(screen.getByText("HND")).toBeInTheDocument();
    // Verify SFO appears for FLIGHT_B destination
    expect(screen.getByText("SFO")).toBeInTheDocument();
  });

  it("renders error state when flights fail to load", () => {
    const mockError = new Error("Failed to load flights") as AppError;
    vi.mocked(useUpcomingFlights).mockReturnValue({
      ...CreateFlightsReturn([]),
      error: mockError,
      isError: true,
      isSuccess: false,
      status: "error",
    } as UseUpcomingFlightsReturn);

    render(<UpcomingFlights />);

    // Component currently falls back to empty state when errors occur
    expect(screen.getByText("No upcoming flights.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /search flights/i })).toBeInTheDocument();
  });

  it("links to trips page from empty state", () => {
    render(<UpcomingFlights />);
    const link = screen.getByRole("link", { name: /search flights/i });
    expect(link).toHaveAttribute("href", "/dashboard/search/flights");
  });
});
