/** @vitest-environment jsdom */

import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock Lucide icons
vi.mock("lucide-react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("lucide-react")>();
  return {
    ...actual,
    HistoryIcon: () => <span data-testid="history-icon" />,
    HotelIcon: () => <span data-testid="hotel-icon" />,
    MapPinIcon: () => <span data-testid="map-pin-icon" />,
    PlaneIcon: () => <span data-testid="plane-icon" />,
    SparklesIcon: () => <span data-testid="sparkles-icon" />,
  };
});

// Mock search history store
interface MockSearch {
  id: string;
  params: Record<string, unknown>;
  searchType: string;
  timestamp: string;
}
const mockRecentSearches = vi.hoisted(() => vi.fn((): MockSearch[] => []));
vi.mock("@/stores/search-history-store", () => ({
  useSearchHistoryStore: () => ({
    recentSearches: mockRecentSearches(),
  }),
}));

// Mock child components to isolate page tests
vi.mock("@/components/features/search", () => ({
  SearchAnalytics: () => <div data-testid="search-analytics">Analytics</div>,
  SearchCollections: () => <div data-testid="search-collections">Collections</div>,
}));

vi.mock("@/components/layouts/search-layout", () => ({
  SearchLayout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="search-layout">{children}</div>
  ),
}));

import SearchPage from "../page";

describe("SearchPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRecentSearches.mockReturnValue([]);
  });

  it("renders search layout wrapper", () => {
    render(<SearchPage />);
    expect(screen.getByTestId("search-layout")).toBeInTheDocument();
  });

  it("renders search options card with title", () => {
    render(<SearchPage />);
    expect(screen.getByText("Search Options")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Start your search for flights, hotels, activities or destinations"
      )
    ).toBeInTheDocument();
  });

  it("renders all tab triggers", () => {
    render(<SearchPage />);
    expect(screen.getByRole("tab", { name: "All" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Flights" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Hotels" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Activities" })).toBeInTheDocument();
  });

  it("renders quick option cards with correct links", () => {
    render(<SearchPage />);
    expect(screen.getByText("Find Flights")).toBeInTheDocument();
    expect(screen.getByText("Book Hotels")).toBeInTheDocument();
    expect(screen.getByText("Discover Activities")).toBeInTheDocument();
    expect(screen.getByText("Browse Destinations")).toBeInTheDocument();
  });

  it("renders recent searches section", () => {
    render(<SearchPage />);
    expect(screen.getByText("Recent Searches")).toBeInTheDocument();
  });

  it("renders empty state when no recent searches", () => {
    mockRecentSearches.mockReturnValue([]);
    render(<SearchPage />);
    expect(
      screen.getByText(
        "No recent searches yet. Start exploring to build your search history!"
      )
    ).toBeInTheDocument();
  });

  it("renders recent search cards when searches exist", () => {
    mockRecentSearches.mockReturnValue([
      {
        id: "search-1",
        params: { destination: "LAX", origin: "NYC" },
        searchType: "flight",
        timestamp: "2024-01-15T10:00:00Z",
      },
      {
        id: "search-2",
        params: { location: "Paris" },
        searchType: "hotel",
        timestamp: "2024-01-14T09:00:00Z",
      },
    ]);

    render(<SearchPage />);
    expect(screen.getByText("NYC to LAX")).toBeInTheDocument();
    expect(screen.getByText("Paris")).toBeInTheDocument();
    expect(screen.getByText("flight")).toBeInTheDocument();
    expect(screen.getByText("hotel")).toBeInTheDocument();
  });

  it("renders SearchAnalytics component in sidebar", () => {
    render(<SearchPage />);
    expect(screen.getByTestId("search-analytics")).toBeInTheDocument();
  });

  it("renders SearchCollections component in sidebar", () => {
    render(<SearchPage />);
    expect(screen.getByTestId("search-collections")).toBeInTheDocument();
  });

  it("limits displayed searches to 6", () => {
    mockRecentSearches.mockReturnValue(
      Array.from({ length: 10 }, (_, i) => ({
        id: `search-${i}`,
        params: { destination: `City ${i}` },
        searchType: "hotel",
        timestamp: `2024-01-${String(15 - i).padStart(2, "0")}T10:00:00Z`,
      }))
    );

    render(<SearchPage />);
    // Should show exactly 6 cities (City 0 through City 5)
    expect(screen.getByText("City 0")).toBeInTheDocument();
    expect(screen.getByText("City 5")).toBeInTheDocument();
    expect(screen.queryByText("City 6")).not.toBeInTheDocument();
  });
});
