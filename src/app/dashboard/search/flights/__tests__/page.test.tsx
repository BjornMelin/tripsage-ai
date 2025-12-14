/** @vitest-environment jsdom */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock Next.js navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    back: vi.fn(),
    push: vi.fn(),
    replace: vi.fn(),
  }),
  useSearchParams: () => ({
    get: vi.fn(() => null),
  }),
}));

// Mock toast
vi.mock("@/components/ui/use-toast", () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

// Mock stores
const mockInitializeSearch = vi.hoisted(() => vi.fn());
const mockExecuteSearch = vi.hoisted(() => vi.fn());

vi.mock("@/hooks/search/use-search-orchestration", () => ({
  useSearchOrchestration: () => ({
    executeSearch: mockExecuteSearch,
    initializeSearch: mockInitializeSearch,
  }),
}));

// Mock API payload builder
vi.mock("@/components/features/search/filters/api-payload", () => ({
  buildFlightApiPayload: vi.fn(() => ({})),
}));

// Mock child components
vi.mock("@/components/features/search/filters/filter-presets", () => ({
  FilterPresets: () => <div data-testid="filter-presets">Filter Presets</div>,
}));

vi.mock("@/components/features/search/filters/filter-panel", () => ({
  FilterPanel: () => <div data-testid="filter-panel">Filter Panel</div>,
}));

vi.mock("@/components/features/search/forms/flight-search-form", () => ({
  FlightSearchForm: ({ onSearch }: { onSearch: () => void }) => (
    <div data-testid="flight-search-form">
      <button type="button" onClick={onSearch}>
        Search Flights
      </button>
    </div>
  ),
}));

vi.mock("@/components/layouts/search-layout", () => ({
  SearchLayout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="search-layout">{children}</div>
  ),
}));

// Import the client component instead of the RSC shell
import FlightsSearchClient from "../flights-search-client";

describe("FlightsSearchClient", () => {
  const mockOnSubmitServer = vi.fn().mockResolvedValue({});
  // Calculate next year dynamically to match the component
  const nextYear = new Date().getUTCFullYear() + 1;

  const renderWithQueryClient = (ui: React.ReactElement) => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    queryClient.setQueryData(
      ["flights", "popular-routes"],
      [
        {
          date: `May 28, ${nextYear}`,
          destination: "London",
          origin: "New York",
          price: 456,
        },
        {
          date: `Jun 15, ${nextYear}`,
          destination: "Tokyo",
          origin: "Los Angeles",
          price: 789,
        },
        {
          date: `Jun 8, ${nextYear}`,
          destination: "Paris",
          origin: "Chicago",
          price: 567,
        },
      ]
    );
    return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockInitializeSearch.mockReset();
    mockExecuteSearch.mockReset();
    mockExecuteSearch.mockResolvedValue("search-123");
    mockOnSubmitServer.mockClear();
  });

  it("renders search layout wrapper", () => {
    renderWithQueryClient(<FlightsSearchClient onSubmitServer={mockOnSubmitServer} />);
    expect(screen.getByTestId("search-layout")).toBeInTheDocument();
  });

  it("renders FlightSearchForm component", () => {
    renderWithQueryClient(<FlightsSearchClient onSubmitServer={mockOnSubmitServer} />);
    expect(screen.getByTestId("flight-search-form")).toBeInTheDocument();
  });

  it("renders FilterPresets sidebar component", () => {
    renderWithQueryClient(<FlightsSearchClient onSubmitServer={mockOnSubmitServer} />);
    expect(screen.getByTestId("filter-presets")).toBeInTheDocument();
  });

  it("renders Popular Routes card", () => {
    renderWithQueryClient(<FlightsSearchClient onSubmitServer={mockOnSubmitServer} />);
    expect(screen.getByText("Popular Routes")).toBeInTheDocument();
    expect(screen.getByText("Trending flight routes and deals")).toBeInTheDocument();
  });

  it("renders Travel Tips card", () => {
    renderWithQueryClient(<FlightsSearchClient onSubmitServer={mockOnSubmitServer} />);
    expect(screen.getByText("Travel Tips")).toBeInTheDocument();
    expect(
      screen.getByText("Tips to help you find the best flights")
    ).toBeInTheDocument();
  });

  it("invokes onSubmitServer when search form is submitted", async () => {
    renderWithQueryClient(<FlightsSearchClient onSubmitServer={mockOnSubmitServer} />);

    const form = screen.getByTestId("flight-search-form");
    fireEvent.click(within(form).getByRole("button", { name: "Search Flights" }));

    await waitFor(() => {
      expect(mockOnSubmitServer).toHaveBeenCalled();
    });
  });

  it("renders popular route cards", () => {
    renderWithQueryClient(<FlightsSearchClient onSubmitServer={mockOnSubmitServer} />);
    // Route cards display origin → destination with an arrow icon between them
    // Check that route information is rendered (prices indicate route cards exist)
    expect(screen.getByText("$456")).toBeInTheDocument();
    expect(screen.getByText("$789")).toBeInTheDocument();
    expect(screen.getByText("$567")).toBeInTheDocument();
    // Check for dates (using dynamic year)
    expect(screen.getByText(`May 28, ${nextYear}`)).toBeInTheDocument();
    expect(screen.getByText(`Jun 15, ${nextYear}`)).toBeInTheDocument();
    expect(screen.getByText(`Jun 8, ${nextYear}`)).toBeInTheDocument();
  });

  it("renders travel tips content", () => {
    renderWithQueryClient(<FlightsSearchClient onSubmitServer={mockOnSubmitServer} />);
    expect(
      screen.getByText("Book 1-3 months in advance for the best prices")
    ).toBeInTheDocument();
    expect(screen.getByText("Consider nearby airports")).toBeInTheDocument();
    expect(screen.getByText("Be flexible with dates if possible")).toBeInTheDocument();
  });

  it("initializes search type on mount", () => {
    renderWithQueryClient(<FlightsSearchClient onSubmitServer={mockOnSubmitServer} />);

    expect(mockInitializeSearch).toHaveBeenCalledWith("flight");
  });
});
