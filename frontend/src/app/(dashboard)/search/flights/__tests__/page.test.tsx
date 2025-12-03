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

vi.mock("@/hooks/search/use-search-orchestration", () => ({
  useSearchOrchestration: () => ({
    executeSearch: mockExecuteSearch,
    initializeSearch: mockInitializeSearch,
  }),
}));

// Mock child components
vi.mock("@/components/features/search/filter-presets", () => ({
  FilterPresets: () => <div data-testid="filter-presets">Filter Presets</div>,
}));

vi.mock("@/components/features/search/filter-panel", () => ({
  FilterPanel: () => <div data-testid="filter-panel">Filter Panel</div>,
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

// Import the client component instead of the RSC shell
import FlightsSearchClient from "../flights-search-client";

describe("FlightsSearchClient", () => {
  const mockOnSubmitServer = vi.fn().mockResolvedValue({});
  // Calculate next year dynamically to match the component
  const nextYear = new Date().getUTCFullYear() + 1;

  beforeEach(() => {
    vi.clearAllMocks();
    mockInitializeSearch.mockReset();
    mockExecuteSearch.mockReset();
    mockExecuteSearch.mockResolvedValue("search-123");
    mockOnSubmitServer.mockClear();
  });

  it("renders search layout wrapper", () => {
    render(<FlightsSearchClient onSubmitServer={mockOnSubmitServer} />);
    expect(screen.getByTestId("search-layout")).toBeInTheDocument();
  });

  it("renders FlightSearchForm component", () => {
    render(<FlightsSearchClient onSubmitServer={mockOnSubmitServer} />);
    expect(screen.getByTestId("flight-search-form")).toBeInTheDocument();
  });

  it("renders FilterPresets sidebar component", () => {
    render(<FlightsSearchClient onSubmitServer={mockOnSubmitServer} />);
    expect(screen.getByTestId("filter-presets")).toBeInTheDocument();
  });

  it("renders Popular Routes card", () => {
    render(<FlightsSearchClient onSubmitServer={mockOnSubmitServer} />);
    expect(screen.getByText("Popular Routes")).toBeInTheDocument();
    expect(screen.getByText("Trending flight routes and deals")).toBeInTheDocument();
  });

  it("renders Travel Tips card", () => {
    render(<FlightsSearchClient onSubmitServer={mockOnSubmitServer} />);
    expect(screen.getByText("Travel Tips")).toBeInTheDocument();
    expect(
      screen.getByText("Tips to help you find the best flights")
    ).toBeInTheDocument();
  });

  it("renders popular route cards", () => {
    render(<FlightsSearchClient onSubmitServer={mockOnSubmitServer} />);
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
    render(<FlightsSearchClient onSubmitServer={mockOnSubmitServer} />);
    expect(
      screen.getByText("Book 1-3 months in advance for the best prices")
    ).toBeInTheDocument();
    expect(screen.getByText("Consider nearby airports")).toBeInTheDocument();
    expect(screen.getByText("Be flexible with dates if possible")).toBeInTheDocument();
  });

  it("initializes search type on mount", () => {
    render(<FlightsSearchClient onSubmitServer={mockOnSubmitServer} />);

    expect(mockInitializeSearch).toHaveBeenCalledWith("flight");
  });
});
