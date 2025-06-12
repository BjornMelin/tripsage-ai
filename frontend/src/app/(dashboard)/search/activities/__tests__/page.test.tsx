/**
 * @vitest-environment jsdom
 */

import { useActivitySearch } from "@/hooks/use-activity-search";
import { useSearchStore } from "@/stores/search-store";
import type { Activity } from "@/types/search";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useSearchParams } from "next/navigation";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ActivitiesSearchPage from "../page";

// Mock Next.js navigation
vi.mock("next/navigation", () => ({
  useSearchParams: vi.fn(),
}));

// Mock the hooks
vi.mock("@/hooks/use-activity-search", () => ({
  useActivitySearch: vi.fn(),
}));

vi.mock("@/stores/search-store", () => ({
  useSearchStore: vi.fn(),
}));

// Define proper types for mocked functions
const mockSearchActivities = vi.fn();

interface MockActivitySearch {
  searchActivities: typeof mockSearchActivities;
  isSearching: boolean;
  searchError: { message: string } | null;
}

interface MockSearchStore {
  results: { activities: Activity[] };
  isLoading: boolean;
  error: string | null;
  hasResults: boolean;
  isSearching: boolean;
}

const mockActivitySearch: MockActivitySearch = {
  searchActivities: mockSearchActivities,
  isSearching: false,
  searchError: null,
};

const mockSearchStore: MockSearchStore = {
  results: { activities: [] },
  isLoading: false,
  error: null,
  hasResults: false,
  isSearching: false,
};

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

const mockActivities: Activity[] = [
  {
    id: "activity-1",
    name: "Central Park Walking Tour",
    type: "cultural",
    location: "Central Park, New York",
    date: "2024-07-01",
    duration: 2.5,
    price: 45,
    rating: 4.7,
    description: "Discover the hidden gems of Central Park with an expert guide.",
    images: ["https://example.com/image1.jpg"],
    coordinates: { lat: 40.7829, lng: -73.9654 },
  },
  {
    id: "activity-2",
    name: "Brooklyn Food Tour",
    type: "food",
    location: "Brooklyn, New York",
    date: "2024-07-01",
    duration: 3,
    price: 85,
    rating: 4.9,
    description: "Taste the best of Brooklyn's diverse food scene.",
    images: ["https://example.com/image2.jpg"],
    coordinates: { lat: 40.6782, lng: -73.9442 },
  },
];

// Mock URLSearchParams for tests
const mockSearchParams = new URLSearchParams();

describe("ActivitiesSearchPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useActivitySearch).mockReturnValue(mockActivitySearch);
    vi.mocked(useSearchStore).mockReturnValue(mockSearchStore);
    vi.mocked(useSearchParams).mockReturnValue(mockSearchParams);
  });

  it("renders the page header correctly", () => {
    render(<ActivitiesSearchPage />, { wrapper: createWrapper() });

    expect(screen.getByText("Search Activities")).toBeInTheDocument();
    expect(
      screen.getByText("Discover exciting activities and experiences for your trip")
    ).toBeInTheDocument();
  });

  it("renders the activity search form", () => {
    render(<ActivitiesSearchPage />, { wrapper: createWrapper() });

    expect(screen.getByText("Activity Search")).toBeInTheDocument();
    expect(screen.getByLabelText(/location/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /search activities/i })
    ).toBeInTheDocument();
  });

  it("shows initial empty state", () => {
    render(<ActivitiesSearchPage />, { wrapper: createWrapper() });

    expect(
      screen.getByText("Use the search form to find activities at your destination")
    ).toBeInTheDocument();
  });

  it("shows loading state during search", () => {
    vi.mocked(useActivitySearch).mockReturnValue({
      ...mockActivitySearch,
      isSearching: true,
    });

    render(<ActivitiesSearchPage />, { wrapper: createWrapper() });

    expect(screen.getByText("Searching activities...")).toBeInTheDocument();
  });

  it("shows loading state from store", () => {
    vi.mocked(useSearchStore).mockReturnValue({
      ...mockSearchStore,
      isSearching: true,
    });

    render(<ActivitiesSearchPage />, { wrapper: createWrapper() });

    expect(screen.getByText("Searching activities...")).toBeInTheDocument();
  });

  it("displays search results when available", () => {
    vi.mocked(useSearchStore).mockReturnValue({
      ...mockSearchStore,
      results: { activities: mockActivities },
      hasResults: true,
    });

    render(<ActivitiesSearchPage />, { wrapper: createWrapper() });

    expect(screen.getByText("2 Activities Found")).toBeInTheDocument();
    expect(screen.getByText("Central Park Walking Tour")).toBeInTheDocument();
    expect(screen.getByText("Brooklyn Food Tour")).toBeInTheDocument();
  });

  it("handles search form submission", async () => {
    render(<ActivitiesSearchPage />, { wrapper: createWrapper() });

    // Fill out the search form
    fireEvent.change(screen.getByLabelText(/location/i), {
      target: { value: "New York" },
    });
    fireEvent.change(screen.getByLabelText(/start date/i), {
      target: { value: "2024-07-01" },
    });
    fireEvent.change(screen.getByLabelText(/end date/i), {
      target: { value: "2024-07-03" },
    });

    const submitButton = screen.getByRole("button", {
      name: /search activities/i,
    });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockSearchActivities).toHaveBeenCalledWith({
        destination: "New York",
        startDate: "2024-07-01",
        endDate: "2024-07-03",
        adults: 1,
        children: 0,
        infants: 0,
        categories: [],
      });
    });
  });

  it("handles activity selection", () => {
    vi.mocked(useSearchStore).mockReturnValue({
      ...mockSearchStore,
      results: { activities: mockActivities },
      hasResults: true,
    });

    const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});

    render(<ActivitiesSearchPage />, { wrapper: createWrapper() });

    const selectButtons = screen.getAllByRole("button", { name: /select/i });
    fireEvent.click(selectButtons[0]);

    expect(consoleSpy).toHaveBeenCalledWith("Selected activity:", mockActivities[0]);

    consoleSpy.mockRestore();
  });

  it("handles activity comparison", () => {
    vi.mocked(useSearchStore).mockReturnValue({
      ...mockSearchStore,
      results: { activities: mockActivities },
      hasResults: true,
    });

    const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});

    render(<ActivitiesSearchPage />, { wrapper: createWrapper() });

    const compareButtons = screen.getAllByRole("button", { name: /compare/i });
    fireEvent.click(compareButtons[0]);

    expect(consoleSpy).toHaveBeenCalledWith("Compare activity:", mockActivities[0]);

    consoleSpy.mockRestore();
  });

  it("shows error message when search fails", () => {
    vi.mocked(useActivitySearch).mockReturnValue({
      ...mockActivitySearch,
      searchError: { message: "Network error" },
    });

    render(<ActivitiesSearchPage />, { wrapper: createWrapper() });

    expect(screen.getByText("Network error")).toBeInTheDocument();
  });

  it("shows error message from store", () => {
    vi.mocked(useSearchStore).mockReturnValue({
      ...mockSearchStore,
      error: "Something went wrong",
    });

    render(<ActivitiesSearchPage />, { wrapper: createWrapper() });

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("shows generic error message when no specific error", () => {
    vi.mocked(useActivitySearch).mockReturnValue({
      ...mockActivitySearch,
      searchError: {} as { message: string },
    });

    render(<ActivitiesSearchPage />, { wrapper: createWrapper() });

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("displays activity selection modal", async () => {
    vi.mocked(useSearchStore).mockReturnValue({
      ...mockSearchStore,
      results: { activities: mockActivities },
      hasResults: true,
    });

    render(<ActivitiesSearchPage />, { wrapper: createWrapper() });

    const selectButtons = screen.getAllByRole("button", { name: /select/i });
    fireEvent.click(selectButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Activity Selected")).toBeInTheDocument();
      expect(
        screen.getByText("You selected: Central Park Walking Tour")
      ).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /close/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /add to trip/i })).toBeInTheDocument();
    });
  });

  it("closes activity selection modal", async () => {
    vi.mocked(useSearchStore).mockReturnValue({
      ...mockSearchStore,
      results: { activities: mockActivities },
      hasResults: true,
    });

    render(<ActivitiesSearchPage />, { wrapper: createWrapper() });

    // Select an activity to open modal
    const selectButtons = screen.getAllByRole("button", { name: /select/i });
    fireEvent.click(selectButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Activity Selected")).toBeInTheDocument();
    });

    // Close the modal
    const closeButton = screen.getByRole("button", { name: /close/i });
    fireEvent.click(closeButton);

    await waitFor(() => {
      expect(screen.queryByText("Activity Selected")).not.toBeInTheDocument();
    });
  });

  it("handles add to trip action", async () => {
    vi.mocked(useSearchStore).mockReturnValue({
      ...mockSearchStore,
      results: { activities: mockActivities },
      hasResults: true,
    });

    render(<ActivitiesSearchPage />, { wrapper: createWrapper() });

    // Select an activity to open modal
    const selectButtons = screen.getAllByRole("button", { name: /select/i });
    fireEvent.click(selectButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Activity Selected")).toBeInTheDocument();
    });

    // Click add to trip
    const addToTripButton = screen.getByRole("button", {
      name: /add to trip/i,
    });
    fireEvent.click(addToTripButton);

    await waitFor(() => {
      expect(screen.queryByText("Activity Selected")).not.toBeInTheDocument();
    });
  });

  it("renders activity cards with correct props", () => {
    vi.mocked(useSearchStore).mockReturnValue({
      ...mockSearchStore,
      results: { activities: mockActivities },
      hasResults: true,
    });

    render(<ActivitiesSearchPage />, { wrapper: createWrapper() });

    // Check that activity cards are rendered with correct content
    expect(screen.getByText("Central Park Walking Tour")).toBeInTheDocument();
    expect(screen.getByText("Brooklyn Food Tour")).toBeInTheDocument();
    expect(screen.getByText("$45")).toBeInTheDocument();
    expect(screen.getByText("$85")).toBeInTheDocument();
  });

  it("uses correct grid layout for results", () => {
    vi.mocked(useSearchStore).mockReturnValue({
      ...mockSearchStore,
      results: { activities: mockActivities },
      hasResults: true,
    });

    render(<ActivitiesSearchPage />, { wrapper: createWrapper() });

    const resultsContainer = screen
      .getByText("Central Park Walking Tour")
      .closest(".grid");
    expect(resultsContainer).toHaveClass("grid-cols-1", "md:grid-cols-2");
  });

  it("shows empty results when activities array is empty", () => {
    vi.mocked(useSearchStore).mockReturnValue({
      ...mockSearchStore,
      results: { activities: [] },
    });

    render(<ActivitiesSearchPage />, { wrapper: createWrapper() });

    expect(
      screen.getByText("Use the search form to find activities at your destination")
    ).toBeInTheDocument();
  });
});
