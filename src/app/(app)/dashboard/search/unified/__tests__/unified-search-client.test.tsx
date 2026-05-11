/** @vitest-environment jsdom */

import type {
  FlightResult,
  FlightSearchFormData,
  HotelResult,
  HotelSearchFormData,
} from "@schemas/search";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Result, ResultError } from "@/lib/result";
import { MOCK_HOTEL_RESULTS } from "@/mocks/unified-search-mocks";
import UnifiedSearchClient from "../unified-search-client";

const mockToast = vi.hoisted(() => vi.fn());

vi.mock("@/components/ui/use-toast", () => ({
  useToast: () => ({ toast: mockToast }),
}));

vi.mock("@/components/layouts/search-layout", () => ({
  SearchLayout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="search-layout">{children}</div>
  ),
}));

vi.mock("@/components/ui/tabs", async () => {
  const ReactModule = await import("react");
  type TabsContextValue = {
    onValueChange: (value: string) => void;
    value: string;
  };
  const TabsContext = ReactModule.createContext<TabsContextValue>({
    onValueChange: () => undefined,
    value: "",
  });

  return {
    Tabs: ({
      children,
      onValueChange,
      value,
    }: {
      children: React.ReactNode;
      onValueChange: (value: string) => void;
      value: string;
    }) => (
      <TabsContext.Provider value={{ onValueChange, value }}>
        <div>{children}</div>
      </TabsContext.Provider>
    ),
    TabsContent: ({
      children,
      value,
    }: {
      children: React.ReactNode;
      value: string;
    }) => {
      const context = ReactModule.useContext(TabsContext);
      return context.value === value ? <div role="tabpanel">{children}</div> : null;
    },
    TabsList: ({ children }: { children: React.ReactNode }) => (
      <div role="tablist">{children}</div>
    ),
    TabsTrigger: ({
      children,
      value,
    }: {
      children: React.ReactNode;
      value: string;
    }) => {
      const context = ReactModule.useContext(TabsContext);
      return (
        <button
          aria-selected={context.value === value}
          onClick={() => context.onValueChange(value)}
          role="tab"
          type="button"
        >
          {children}
        </button>
      );
    },
  };
});

vi.mock("@/features/search/components/forms/flight-search-form", () => ({
  FlightSearchForm: ({
    onSearch,
  }: {
    onSearch: (params: FlightSearchFormData) => Promise<void> | void;
  }) => (
    <button
      type="button"
      onClick={() => {
        onSearch({
          cabinClass: "economy",
          departureDate: "2026-06-01",
          destination: "LAX",
          directOnly: false,
          origin: "JFK",
          passengers: { adults: 1, children: 0, infants: 0 },
          returnDate: "2026-06-05",
          tripType: "round-trip",
        });
      }}
    >
      Run Flight Search
    </button>
  ),
}));

vi.mock("@/features/search/components/forms/hotel-search-form", () => ({
  HotelSearchForm: ({
    onSearch,
  }: {
    onSearch: (params: HotelSearchFormData) => Promise<void> | void;
  }) => (
    <button
      type="button"
      onClick={() => {
        onSearch({
          adults: 2,
          amenities: [],
          checkIn: "2026-06-01",
          checkOut: "2026-06-05",
          children: 0,
          location: "Paris",
          priceRange: { max: 1000, min: 0 },
          rating: 0,
          rooms: 1,
        });
      }}
    >
      Run Hotel Search
    </button>
  ),
}));

vi.mock("@/features/search/components/results/flight-results", () => ({
  FlightResults: ({ results }: { results: FlightResult[] }) => (
    <div data-testid="flight-results">
      {results.map((flight) => (
        <span key={flight.id}>{flight.airline}</span>
      ))}
    </div>
  ),
}));

vi.mock("@/features/search/components/results/hotel-results", () => ({
  HotelResults: ({ results }: { results: HotelResult[] }) => (
    <div data-testid="hotel-results">
      {results.map((hotel) => (
        <span key={hotel.id}>{hotel.name}</span>
      ))}
    </div>
  ),
}));

type HotelSearchResult = Result<HotelResult[], ResultError>;

function createDeferred<T>() {
  let resolve: (value: T) => void = () => undefined;
  const promise = new Promise<T>((resolver) => {
    resolve = resolver;
  });
  return { promise, resolve };
}

describe("UnifiedSearchClient", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("ignores stale hotel results after a newer search starts", async () => {
    const staleSearch = createDeferred<HotelSearchResult>();
    const latestSearch = createDeferred<HotelSearchResult>();
    const onSearchHotels = vi
      .fn<
        (
          params: HotelSearchFormData,
          signal?: AbortSignal
        ) => Promise<HotelSearchResult>
      >()
      .mockReturnValueOnce(staleSearch.promise)
      .mockReturnValueOnce(latestSearch.promise);

    render(<UnifiedSearchClient onSearchHotels={onSearchHotels} />);

    fireEvent.click(screen.getByRole("tab", { name: "Hotels" }));
    const searchButton = screen.getByRole("button", { name: "Run Hotel Search" });
    fireEvent.click(searchButton);
    fireEvent.click(searchButton);

    await act(async () => {
      latestSearch.resolve({
        data: [{ ...MOCK_HOTEL_RESULTS[1], name: "Latest Hotel" }],
        ok: true,
      });
      await latestSearch.promise;
    });

    await waitFor(() => expect(screen.getByText("Latest Hotel")).toBeInTheDocument());

    await act(async () => {
      staleSearch.resolve({
        data: [{ ...MOCK_HOTEL_RESULTS[0], name: "Stale Hotel" }],
        ok: true,
      });
      await staleSearch.promise;
    });

    expect(screen.getByText("Latest Hotel")).toBeInTheDocument();
    expect(screen.queryByText("Stale Hotel")).not.toBeInTheDocument();
  });
});
