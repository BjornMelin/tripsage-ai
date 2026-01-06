/** @vitest-environment jsdom */

import type { SearchHistoryItem } from "@schemas/stores";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock the onSearch function
const MockOnSearch = vi.fn();

const MockSearchHistory = vi.hoisted(() => ({
  recentFlight: [] as SearchHistoryItem[],
}));

vi.mock("@/features/search/store/search-history", () => ({
  useSearchHistoryStore: (
    selector: (state: {
      recentSearchesByType: { flight: SearchHistoryItem[] };
    }) => unknown
  ) => selector({ recentSearchesByType: { flight: MockSearchHistory.recentFlight } }),
}));

function RenderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("FlightSearchForm", () => {
  beforeEach(() => {
    // Clear mock calls between tests
    // MSW handlers in src/test/msw/handlers/api-routes.ts provide
    // /api/flights/popular-destinations responses
    MockOnSearch.mockClear();
    MockSearchHistory.recentFlight = [];
    vi.restoreAllMocks();
  });

  it("renders the form correctly (aligned with current UI)", async () => {
    const { FlightSearchForm } = await import("../flight-search-form");
    RenderWithQueryClient(<FlightSearchForm onSearch={MockOnSearch} />);

    // Title and trip type buttons
    expect(screen.getByText("Find Flights")).toBeInTheDocument();
    expect(screen.getByText("Round Trip")).toBeInTheDocument();
    expect(screen.getByText("One Way")).toBeInTheDocument();
    expect(screen.getByText("Multi-City")).toBeInTheDocument();

    // From/To labels
    expect(screen.getByText("From")).toBeInTheDocument();
    expect(screen.getByText("To")).toBeInTheDocument();

    // Date labels
    expect(screen.getByText("Departure")).toBeInTheDocument();
    expect(screen.getByText("Return")).toBeInTheDocument();

    // Passenger label hints
    expect(screen.getByText("Adults")).toBeInTheDocument();
    expect(screen.getByText(/Children \(2-11\)/)).toBeInTheDocument();

    // Primary actions
    expect(screen.getByText("Search Flights")).toBeInTheDocument();
    expect(screen.getByText("Flexible Dates")).toBeInTheDocument();
  });

  it("handles form submission with valid data", async () => {
    const { FlightSearchForm } = await import("../flight-search-form");
    RenderWithQueryClient(<FlightSearchForm onSearch={MockOnSearch} />);

    // Fill in required fields matching current placeholders/labels
    fireEvent.change(screen.getByPlaceholderText("Departure city or airport"), {
      target: { value: "New York" },
    });
    fireEvent.change(screen.getByPlaceholderText("Destination city or airport"), {
      target: { value: "London" },
    });

    // Date inputs (type=date) are not directly label-associated due to wrapper structure;
    // select by role order within the form.
    const container = document.body;
    const dateInputs = Array.from(
      container.querySelectorAll('input[type="date"]')
    ) as HTMLInputElement[];
    const [departureDateInput, returnDateInput] = dateInputs;

    fireEvent.change(departureDateInput, { target: { value: "2099-08-15" } });
    fireEvent.change(returnDateInput, { target: { value: "2099-08-25" } });

    // Submit the form (ensure form submit event is dispatched)
    const submitBtn = screen.getByText("Search Flights");
    const formEl = submitBtn.closest("form") as HTMLFormElement;
    expect(formEl).toBeTruthy();
    if (formEl) {
      fireEvent.submit(formEl);
    }

    // onSearch receives schema-validated FlightSearchFormData shape (async)
    await vi.waitFor(() => expect(MockOnSearch).toHaveBeenCalledTimes(1));
    expect(MockOnSearch).toHaveBeenCalledWith({
      cabinClass: "economy",
      departureDate: "2099-08-15",
      destination: "London",
      directOnly: false,
      excludedAirlines: [],
      maxStops: undefined,
      origin: "New York",
      passengers: { adults: 1, children: 0, infants: 0 },
      preferredAirlines: [],
      returnDate: "2099-08-25",
      tripType: "round-trip",
    });
  });

  it("keeps placeholders intact when autocomplete-like selections occur", async () => {
    const { FlightSearchForm } = await import("../flight-search-form");
    RenderWithQueryClient(<FlightSearchForm onSearch={MockOnSearch} />);

    const originInput = screen.getByPlaceholderText(
      "Departure city or airport"
    ) as HTMLInputElement;
    const destinationInput = screen.getByPlaceholderText(
      "Destination city or airport"
    ) as HTMLInputElement;

    fireEvent.change(originInput, {
      target: { value: "San Francisco International (SFO)" },
    });
    fireEvent.change(destinationInput, {
      target: { value: "Heathrow (LHR)" },
    });

    expect(originInput.placeholder).toBe("Departure city or airport");
    expect(destinationInput.placeholder).toBe("Destination city or airport");
  });

  it("fills destination when selecting a popular destination chip", async () => {
    const { FlightSearchForm } = await import("../flight-search-form");
    RenderWithQueryClient(<FlightSearchForm onSearch={MockOnSearch} />);

    const destinationChip = await screen.findByText("New York");
    fireEvent.click(destinationChip);

    const destinationInput = screen.getByPlaceholderText(
      "Destination city or airport"
    ) as HTMLInputElement;

    await waitFor(() => expect(destinationInput.value).toBe("NYC"));
  });

  it("normalizes legacy passenger fields when selecting a recent search", async () => {
    const { FlightSearchForm } = await import("../flight-search-form");
    MockSearchHistory.recentFlight = [
      {
        id: "recent-legacy-1",
        params: {
          adults: 2,
          cabinClass: "economy",
          departureDate: "2099-08-15",
          destination: "LHR",
          directOnly: false,
          excludedAirlines: [],
          maxStops: undefined,
          origin: "SFO",
          preferredAirlines: [],
        },
        searchType: "flight",
        timestamp: "2025-01-01T00:00:00.000Z",
      },
    ];

    RenderWithQueryClient(<FlightSearchForm onSearch={MockOnSearch} />);

    const recentButton = await screen.findByRole("button", { name: /SFO.*LHR/ });
    fireEvent.click(recentButton);

    const submitBtn = screen.getByRole("button", { name: "Search Flights" });
    await waitFor(() => expect(submitBtn).not.toBeDisabled());
    fireEvent.click(submitBtn);

    await vi.waitFor(() => expect(MockOnSearch).toHaveBeenCalledTimes(1));
    expect(MockOnSearch).toHaveBeenCalledWith(
      expect.objectContaining({
        destination: "LHR",
        origin: "SFO",
        passengers: { adults: 2, children: 0, infants: 0 },
        tripType: "one-way",
      })
    );
  });

  it("prefers nested passengers when selecting a recent search", async () => {
    const { FlightSearchForm } = await import("../flight-search-form");
    MockSearchHistory.recentFlight = [
      {
        id: "recent-passengers-1",
        params: {
          adults: 1,
          cabinClass: "economy",
          departureDate: "2099-08-15",
          destination: "LHR",
          origin: "SFO",
          passengers: { adults: 3, children: 1, infants: 0 },
        },
        searchType: "flight",
        timestamp: "2025-01-01T00:00:00.000Z",
      },
    ];

    RenderWithQueryClient(<FlightSearchForm onSearch={MockOnSearch} />);

    const recentButton = await screen.findByRole("button", { name: /SFO.*LHR/ });
    fireEvent.click(recentButton);

    const submitBtn = screen.getByRole("button", { name: "Search Flights" });
    await waitFor(() => expect(submitBtn).not.toBeDisabled());
    fireEvent.click(submitBtn);

    await vi.waitFor(() => expect(MockOnSearch).toHaveBeenCalledTimes(1));
    expect(MockOnSearch).toHaveBeenCalledWith(
      expect.objectContaining({
        passengers: { adults: 3, children: 1, infants: 0 },
      })
    );
  });

  it("does not render recent quick-select items when stored params are invalid", async () => {
    const { FlightSearchForm } = await import("../flight-search-form");
    MockSearchHistory.recentFlight = [
      {
        id: "recent-invalid-1",
        params: { origin: 123 },
        searchType: "flight",
        timestamp: "2025-01-01T00:00:00.000Z",
      },
    ];

    RenderWithQueryClient(<FlightSearchForm onSearch={MockOnSearch} />);

    expect(screen.queryByText(/Recent searches/i)).not.toBeInTheDocument();
  });
});
