/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";
import DestinationsSearchPage from "../page";
import type { ReactNode } from "react";

// Mock the hooks and stores
vi.mock("@/stores/search-store", () => ({
  useSearchStore: vi.fn(() => ({
    results: { destinations: [] },
    isLoading: false,
    error: null,
    destinationParams: { query: "" },
    setSearchType: vi.fn(),
  })),
}));

vi.mock("@/hooks/use-destination-search", () => ({
  useDestinationSearch: vi.fn(() => ({
    searchDestinationsMock: vi.fn(),
    isSearching: false,
    searchError: null,
    resetSearch: vi.fn(),
  })),
}));

// Mock the components to avoid complex dependency issues
vi.mock("@/components/features/search/destination-search-form", () => ({
  DestinationSearchForm: ({ onSearch }: { onSearch: Function }) => (
    <div data-testid="destination-search-form">
      <button
        type="button"
        onClick={() =>
          onSearch({ query: "Paris", types: ["locality"], limit: 10 })
        }
      >
        Mock Search
      </button>
    </div>
  ),
}));

vi.mock("@/components/features/search/destination-card", () => ({
  DestinationCard: ({
    destination,
    onSelect,
    onCompare,
    onViewDetails,
  }: any) => (
    <div data-testid="destination-card">
      <h3>{destination.name}</h3>
      <button type="button" onClick={() => onSelect?.(destination)}>
        Select
      </button>
      <button type="button" onClick={() => onCompare?.(destination)}>
        Compare
      </button>
      <button type="button" onClick={() => onViewDetails?.(destination)}>
        Details
      </button>
    </div>
  ),
}));

const mockDestination = {
  id: "dest_paris_fr",
  name: "Paris",
  description: "The City of Light",
  formattedAddress: "Paris, France",
  types: ["locality", "political"],
  coordinates: { lat: 48.8566, lng: 2.3522 },
  rating: 4.6,
  country: "France",
  bestTimeToVisit: ["Apr", "May", "Jun"],
};

// Create a wrapper for React Query
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
};

describe("DestinationsSearchPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the page header correctly", () => {
    const wrapper = createWrapper();
    render(<DestinationsSearchPage />, { wrapper });

    expect(screen.getByText("Destination Search")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Discover amazing destinations around the world with intelligent search and autocomplete"
      )
    ).toBeInTheDocument();
  });

  it("renders the search form", () => {
    const wrapper = createWrapper();
    render(<DestinationsSearchPage />, { wrapper });

    expect(screen.getByTestId("destination-search-form")).toBeInTheDocument();
  });

  it("displays empty state when no search has been performed", () => {
    const wrapper = createWrapper();
    render(<DestinationsSearchPage />, { wrapper });

    expect(
      screen.getByText("Discover Amazing Destinations")
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Search for cities, countries, landmarks, or regions to find your next travel destination."
      )
    ).toBeInTheDocument();
  });

  it("handles search form submission", async () => {
    const mockSearchDestinationsMock = vi.fn();
    const { useDestinationSearch } = await import(
      "@/hooks/use-destination-search"
    );

    (useDestinationSearch as any).mockReturnValue({
      searchDestinationsMock: mockSearchDestinationsMock,
      isSearching: false,
      searchError: null,
      resetSearch: vi.fn(),
    });

    const wrapper = createWrapper();
    const user = userEvent.setup();
    render(<DestinationsSearchPage />, { wrapper });

    const searchButton = screen.getByText("Mock Search");
    await user.click(searchButton);

    expect(mockSearchDestinationsMock).toHaveBeenCalledWith({
      query: "Paris",
      types: ["locality"],
      limit: 10,
    });
  });

  it("displays search results when available", () => {
    const { useSearchStore } = require("@/stores/search-store");

    useSearchStore.mockReturnValue({
      results: { destinations: [mockDestination] },
      isLoading: false,
      error: null,
      destinationParams: { query: "Paris" },
      setSearchType: vi.fn(),
    });

    const wrapper = createWrapper();
    render(<DestinationsSearchPage />, { wrapper });

    expect(
      screen.getByText("Search Results (1 destinations)")
    ).toBeInTheDocument();
    expect(screen.getByTestId("destination-card")).toBeInTheDocument();
    expect(screen.getByText("Paris")).toBeInTheDocument();
  });

  it("displays loading state when searching", () => {
    const { useSearchStore } = require("@/stores/search-store");

    useSearchStore.mockReturnValue({
      results: { destinations: [] },
      isLoading: true,
      error: null,
      destinationParams: { query: "Paris" },
      setSearchType: vi.fn(),
    });

    const wrapper = createWrapper();
    render(<DestinationsSearchPage />, { wrapper });

    expect(screen.getByText("Searching destinations...")).toBeInTheDocument();
  });

  it("displays error state when search fails", () => {
    const { useSearchStore } = require("@/stores/search-store");

    useSearchStore.mockReturnValue({
      results: { destinations: [] },
      isLoading: false,
      error: "Search failed",
      destinationParams: { query: "Paris" },
      setSearchType: vi.fn(),
    });

    const wrapper = createWrapper();
    render(<DestinationsSearchPage />, { wrapper });

    expect(screen.getByText("Search failed")).toBeInTheDocument();
    expect(screen.getByText("Try Again")).toBeInTheDocument();
  });

  it("displays no results state when search returns empty", () => {
    const { useSearchStore } = require("@/stores/search-store");

    useSearchStore.mockReturnValue({
      results: { destinations: [] },
      isLoading: false,
      error: null,
      destinationParams: { query: "NonExistentPlace" },
      setSearchType: vi.fn(),
    });

    const wrapper = createWrapper();
    render(<DestinationsSearchPage />, { wrapper });

    expect(screen.getByText("No destinations found")).toBeInTheDocument();
    expect(
      screen.getByText("Try adjusting your search terms or destination types")
    ).toBeInTheDocument();
  });

  it("handles destination selection", async () => {
    // Mock window.alert
    const alertSpy = vi.spyOn(window, "alert").mockImplementation(() => {});

    const { useSearchStore } = require("@/stores/search-store");

    useSearchStore.mockReturnValue({
      results: { destinations: [mockDestination] },
      isLoading: false,
      error: null,
      destinationParams: { query: "Paris" },
      setSearchType: vi.fn(),
    });

    const wrapper = createWrapper();
    const user = userEvent.setup();
    render(<DestinationsSearchPage />, { wrapper });

    const selectButton = screen.getByText("Select");
    await user.click(selectButton);

    expect(alertSpy).toHaveBeenCalledWith("Selected: Paris");

    alertSpy.mockRestore();
  });

  it("handles destination comparison", async () => {
    const { useSearchStore } = require("@/stores/search-store");

    useSearchStore.mockReturnValue({
      results: { destinations: [mockDestination] },
      isLoading: false,
      error: null,
      destinationParams: { query: "Paris" },
      setSearchType: vi.fn(),
    });

    const wrapper = createWrapper();
    const user = userEvent.setup();
    render(<DestinationsSearchPage />, { wrapper });

    const compareButton = screen.getByText("Compare");
    await user.click(compareButton);

    // Should show comparison bar
    await waitFor(() => {
      expect(
        screen.getByText("Compare Destinations (1/3)")
      ).toBeInTheDocument();
    });
  });

  it("handles view details", async () => {
    // Mock window.alert
    const alertSpy = vi.spyOn(window, "alert").mockImplementation(() => {});

    const { useSearchStore } = require("@/stores/search-store");

    useSearchStore.mockReturnValue({
      results: { destinations: [mockDestination] },
      isLoading: false,
      error: null,
      destinationParams: { query: "Paris" },
      setSearchType: vi.fn(),
    });

    const wrapper = createWrapper();
    const user = userEvent.setup();
    render(<DestinationsSearchPage />, { wrapper });

    const detailsButton = screen.getByText("Details");
    await user.click(detailsButton);

    expect(alertSpy).toHaveBeenCalledWith("View details for: Paris");

    alertSpy.mockRestore();
  });

  it("limits comparison to 3 destinations", async () => {
    const destinations = [
      { ...mockDestination, id: "dest1", name: "Paris" },
      { ...mockDestination, id: "dest2", name: "London" },
      { ...mockDestination, id: "dest3", name: "Rome" },
      { ...mockDestination, id: "dest4", name: "Madrid" },
    ];

    const { useSearchStore } = require("@/stores/search-store");

    useSearchStore.mockReturnValue({
      results: { destinations },
      isLoading: false,
      error: null,
      destinationParams: { query: "Europe" },
      setSearchType: vi.fn(),
    });

    // Mock window.alert
    const alertSpy = vi.spyOn(window, "alert").mockImplementation(() => {});

    const wrapper = createWrapper();
    const user = userEvent.setup();
    render(<DestinationsSearchPage />, { wrapper });

    const compareButtons = screen.getAllByText("Compare");

    // Click first 3 compare buttons (should work)
    await user.click(compareButtons[0]);
    await user.click(compareButtons[1]);
    await user.click(compareButtons[2]);

    // Click 4th compare button (should show alert)
    await user.click(compareButtons[3]);

    expect(alertSpy).toHaveBeenCalledWith(
      "You can compare up to 3 destinations at once"
    );

    alertSpy.mockRestore();
  });

  it("opens comparison modal when compare button is clicked", async () => {
    const destinations = [
      { ...mockDestination, id: "dest1", name: "Paris" },
      { ...mockDestination, id: "dest2", name: "London" },
    ];

    const { useSearchStore } = require("@/stores/search-store");

    useSearchStore.mockReturnValue({
      results: { destinations },
      isLoading: false,
      error: null,
      destinationParams: { query: "Europe" },
      setSearchType: vi.fn(),
    });

    const wrapper = createWrapper();
    const user = userEvent.setup();
    render(<DestinationsSearchPage />, { wrapper });

    // Add destinations to comparison
    const compareButtons = screen.getAllByText("Compare");
    await user.click(compareButtons[0]);
    await user.click(compareButtons[1]);

    // Click the compare button in the comparison bar
    const compareBarButton = screen.getByRole("button", { name: "Compare" });
    await user.click(compareBarButton);

    expect(screen.getByText("Destination Comparison")).toBeInTheDocument();
  });
});
