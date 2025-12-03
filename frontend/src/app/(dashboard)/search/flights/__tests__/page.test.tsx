/** @vitest-environment jsdom */

import { render, screen } from "@testing-library/react";
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
const mockSetSearchType = vi.hoisted(() => vi.fn());

vi.mock("@/stores/search-store", () => ({
  useSearchStore: () => ({
    executeSearch: mockExecuteSearch(),
    initializeSearch: mockInitializeSearch(),
  }),
}));

vi.mock("@/stores/search-filters-store", () => ({
  useSearchFiltersStore: () => ({
    setSearchType: mockSetSearchType(),
  }),
}));

// Mock child components
vi.mock("@/components/features/search/filter-presets", () => ({
  FilterPresets: () => <div data-testid="filter-presets">Filter Presets</div>,
}));

vi.mock("@/components/features/search/flight-search-form", () => ({
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

import FlightSearchPage from "../page";

describe("FlightSearchPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockInitializeSearch.mockReturnValue(vi.fn());
    mockExecuteSearch.mockReturnValue(vi.fn().mockResolvedValue("search-123"));
    mockSetSearchType.mockReturnValue(vi.fn());
  });

  it("renders search layout wrapper", () => {
    render(<FlightSearchPage />);
    expect(screen.getByTestId("search-layout")).toBeInTheDocument();
  });

  it("renders FlightSearchForm component", () => {
    render(<FlightSearchPage />);
    expect(screen.getByTestId("flight-search-form")).toBeInTheDocument();
  });

  it("renders FilterPresets sidebar component", () => {
    render(<FlightSearchPage />);
    expect(screen.getByTestId("filter-presets")).toBeInTheDocument();
  });

  it("renders Popular Routes card", () => {
    render(<FlightSearchPage />);
    expect(screen.getByText("Popular Routes")).toBeInTheDocument();
    expect(screen.getByText("Trending flight routes and deals")).toBeInTheDocument();
  });

  it("renders Travel Tips card", () => {
    render(<FlightSearchPage />);
    expect(screen.getByText("Travel Tips")).toBeInTheDocument();
    expect(
      screen.getByText("Tips to help you find the best flights")
    ).toBeInTheDocument();
  });

  it("renders popular route cards", () => {
    render(<FlightSearchPage />);
    // Check for route combinations in popular routes (rendered as "origin to destination")
    expect(screen.getByText(/New York to London/)).toBeInTheDocument();
    expect(screen.getByText(/Los Angeles to Tokyo/)).toBeInTheDocument();
    expect(screen.getByText(/Chicago to Paris/)).toBeInTheDocument();
  });

  it("renders travel tips content", () => {
    render(<FlightSearchPage />);
    expect(
      screen.getByText("Book 1-3 months in advance for the best prices")
    ).toBeInTheDocument();
    expect(screen.getByText("Consider nearby airports")).toBeInTheDocument();
    expect(screen.getByText("Be flexible with dates if possible")).toBeInTheDocument();
  });

  it("initializes search type on mount", () => {
    const initFn = vi.fn();
    const setTypeFn = vi.fn();
    mockInitializeSearch.mockReturnValue(initFn);
    mockSetSearchType.mockReturnValue(setTypeFn);

    render(<FlightSearchPage />);

    expect(initFn).toHaveBeenCalledWith("flight");
    expect(setTypeFn).toHaveBeenCalledWith("flight");
  });
});
