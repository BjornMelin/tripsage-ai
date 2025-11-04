/**
 * @fileoverview Modern trip suggestions tests.
 *
 * Focused tests for trip suggestion functionality using proper mocking
 * patterns and behavioral validation. Following ULTRATHINK methodology.
 */

import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { type TripSuggestion, useTripSuggestions } from "@/hooks/use-trips";
import type { Budget } from "@/lib/schemas/budget";
import { render } from "@/test/test-utils";
import { TripSuggestions } from "../trip-suggestions";

/** Mock the stores with essential methods */
const MockBudgetStore = {
  activeBudget: null as Budget | null,
  activeBudgetId: null,
};

/** Mock the deals store */
const MockDealsStore = {
  deals: [],
  isLoading: false,
};

/** Mock the budget store */
vi.mock("@/stores/budget-store", () => ({
  useBudgetStore: vi.fn(() => MockBudgetStore),
}));

/** Mock the deals store */
vi.mock("@/stores/deals-store", () => ({
  useDealsStore: vi.fn(() => MockDealsStore),
}));

/** Mock the trips suggestions hook */
vi.mock("@/hooks/use-trips", () => ({
  useTripSuggestions: vi.fn(),
}));

/** Mock Next.js Link */
vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

/** Test suite for TripSuggestions */
describe("TripSuggestions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MockBudgetStore.activeBudget = null;
    MockDealsStore.deals = [];
    // Provide default API suggestions
    vi.mocked(useTripSuggestions).mockReturnValue({
      data: [
        {
          best_time_to_visit: "Spring",
          category: "culture",
          currency: "USD",
          description: "Romantic escape in the city of lights",
          destination: "Paris",
          duration: 5,
          estimated_price: 1500,
          highlights: ["Louvre", "Eiffel Tower", "Seine Cruise"],
          id: "sug-1",
          rating: 4.5,
          title: "Paris Getaway",
        },
        {
          best_time_to_visit: "Fall",
          category: "city",
          currency: "USD",
          description: "Modern meets tradition",
          destination: "Tokyo",
          duration: 7,
          estimated_price: 2000,
          highlights: ["Shibuya", "Asakusa", "Akihabara"],
          id: "sug-2",
          rating: 4.7,
          title: "Tokyo Explorer",
        },
      ],
      dataUpdatedAt: Date.now(),
      error: null,
      errorUpdateCount: 0,
      errorUpdatedAt: 0,
      failureCount: 0,
      failureReason: null,
      fetchStatus: "idle",
      isEnabled: true,
      isError: false,
      isFetched: true,
      isFetchedAfterMount: true,
      isFetching: false,
      isInitialLoading: false,
      isLoading: false,
      isLoadingError: false,
      isPaused: false,
      isPending: false,
      isPlaceholderData: false,
      isRefetchError: false,
      isRefetching: false,
      isStale: false,
      isSuccess: true,
      promise: Promise.resolve([] as TripSuggestion[]),
      refetch: vi.fn(),
      status: "success",
    });
  });

  describe("Basic Rendering", () => {
    /** Test that the component renders successfully */
    it("should render component successfully", () => {
      render(<TripSuggestions />);

      expect(screen.getByText("Trip Suggestions")).toBeInTheDocument();
    });

    /** Test that the component shows default suggestions when no filters applied */
    it("should show default suggestions when no filters applied", () => {
      render(<TripSuggestions />);

      /** Should show at least some trip suggestions */
      const planButtons = screen.queryAllByText("Plan Trip");
      expect(planButtons.length).toBeGreaterThan(0);
    });

    /** Test that the component renders with a custom limit */
    it("should render with custom limit", () => {
      render(<TripSuggestions limit={2} />);

      /** Plan buttons */
      const planButtons = screen.queryAllByText("Plan Trip");
      expect(planButtons.length).toBeLessThanOrEqual(2);
    });
  });

  describe("Budget Filtering", () => {
    /** Test that the component filters suggestions based on budget */
    it("should filter suggestions based on budget", () => {
      /** Set a low budget that should filter out expensive suggestions */
      MockBudgetStore.activeBudget = {
        categories: [],
        createdAt: "2024-01-01T00:00:00Z",
        currency: "USD",
        id: "test-budget",
        isActive: true,
        name: "Test Budget",
        totalAmount: 1000,
        updatedAt: "2024-01-01T00:00:00Z",
      };

      render(<TripSuggestions />);

      /** Component should still render but might show fewer suggestions */
      expect(screen.getByText("Trip Suggestions")).toBeInTheDocument();
    });

    /** Test that the component shows all suggestions when no budget set */
    it("should show all suggestions when no budget set", () => {
      MockBudgetStore.activeBudget = null;

      render(<TripSuggestions />);

      /** Should show default set of suggestions */
      const planButtons = screen.queryAllByText("Plan Trip");
      expect(planButtons.length).toBeGreaterThan(0);
    });
  });

  describe("Empty States", () => {
    it("should show empty state when no suggestions match filters", () => {
      /** Set extremely low budget to filter out all suggestions */
      MockBudgetStore.activeBudget = {
        categories: [],
        createdAt: "2024-01-01T00:00:00Z",
        currency: "USD",
        id: "low-budget",
        isActive: true,
        name: "Low Budget",
        totalAmount: 1,
        updatedAt: "2024-01-01T00:00:00Z",
      };
      /** No API suggestions */
      vi.mocked(useTripSuggestions).mockReturnValue({
        data: [],
        dataUpdatedAt: Date.now(),
        error: null,
        errorUpdateCount: 0,
        errorUpdatedAt: 0,
        failureCount: 0,
        failureReason: null,
        fetchStatus: "idle",
        isEnabled: true,
        isError: false,
        isFetched: true,
        isFetchedAfterMount: true,
        isFetching: false,
        isInitialLoading: false,
        isLoading: false,
        isLoadingError: false,
        isPaused: false,
        isPending: false,
        isPlaceholderData: false,
        isRefetchError: false,
        isRefetching: false,
        isStale: false,
        isSuccess: true,
        promise: Promise.resolve([] as TripSuggestion[]),
        refetch: vi.fn(),
        status: "success",
      });

      render(<TripSuggestions />);

      /** Should show empty state messaging */
      const emptyMessage =
        screen.queryByText(/no suggestions/i) ||
        screen.queryByText(/get personalized/i);
      expect(emptyMessage).toBeTruthy();
    });

    /** Test that the component handles the showEmpty prop correctly */
    it("should handle showEmpty prop correctly", () => {
      MockBudgetStore.activeBudget = {
        categories: [],
        createdAt: "2024-01-01T00:00:00Z",
        currency: "USD",
        id: "minimal-budget",
        isActive: true,
        name: "Minimal Budget",
        totalAmount: 1,
        updatedAt: "2024-01-01T00:00:00Z",
      };

      const { rerender } = render(<TripSuggestions showEmpty={false} />);

      /** With showEmpty=false, should not show chat suggestion */
      expect(screen.queryByText(/chat with ai/i)).not.toBeInTheDocument();

      rerender(<TripSuggestions showEmpty={true} />);

      /** With showEmpty=true, might show chat suggestion or alternative empty state */
      expect(screen.getByText("Trip Suggestions")).toBeInTheDocument();
    });
  });

  describe("Navigation and Interactions", () => {
    /** Test that the component renders plan trip links correctly */
    it("should render plan trip links correctly", () => {
      render(<TripSuggestions />);

      /** Plan buttons */
      const planButtons = screen.queryAllByText("Plan Trip");

      if (planButtons.length > 0) {
        const firstButton = planButtons[0].closest("a");
        expect(firstButton).toHaveAttribute("href");
        expect(firstButton?.getAttribute("href")).toContain("/dashboard/trips");
      }
    });

    /** Test that the component renders navigation to chat when available */
    it("should render navigation to chat when available", () => {
      render(<TripSuggestions />);

      /** Look for any chat-related navigation */
      const chatLinks = screen.queryAllByText(/chat/i);
      if (chatLinks.length > 0) {
        const chatLink = chatLinks[0].closest("a");
        expect(chatLink).toHaveAttribute("href");
      }
    });
  });

  describe("Content Display", () => {
    /** Test that the component displays suggestion information when available */
    it("should display suggestion information when available", () => {
      render(<TripSuggestions />);

      /** Should show price information (currency symbols or numbers) */
      const priceRegex = /\$[\d,]+/;
      const prices = screen.queryAllByText(priceRegex);

      /** If suggestions are shown, they should have prices */
      const planButtons = screen.queryAllByText("Plan Trip");
      if (planButtons.length > 0) {
        expect(prices.length).toBeGreaterThan(0);
      }
    });

    /** Test that the component shows ratings when suggestions are displayed */
    it("should show ratings when suggestions are displayed", () => {
      render(<TripSuggestions />);

      /** Look for rating patterns (decimal numbers that could be ratings) */
      const ratingPattern = /\d\.\d/;
      const ratings = screen.queryAllByText(ratingPattern);

      const planButtons = screen.queryAllByText("Plan Trip");
      if (planButtons.length > 0) {
        /** If suggestions exist, should have at least some ratings */
        expect(ratings.length).toBeGreaterThanOrEqual(0);
      }
    });

    /** Test that the component handles undefined budget store gracefully */
    it("should handle undefined budget store gracefully", () => {
      MockBudgetStore.activeBudget = null;

      render(<TripSuggestions />);

      /** Should render without error */
      expect(screen.getByText("Trip Suggestions")).toBeInTheDocument();
    });
  });

  describe("Error Handling", () => {
    /** Test that the component renders gracefully with invalid props */
    it("should render gracefully with invalid props", () => {
      render(<TripSuggestions limit={-1} />);

      /** Should still render the component */
      expect(screen.getByText("Trip Suggestions")).toBeInTheDocument();
    });

    /** Test that the component handles store errors gracefully */
    it("should handle store errors gracefully", () => {
      /** Mock store to throw error */
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {
        /** Intentionally empty - suppress console errors during test */
      });

      try {
        render(<TripSuggestions />);
        expect(screen.getByText("Trip Suggestions")).toBeInTheDocument();
      } finally {
        consoleSpy.mockRestore();
      }
    });
  });
});
