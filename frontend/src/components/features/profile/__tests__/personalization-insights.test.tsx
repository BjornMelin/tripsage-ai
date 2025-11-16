import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PersonalizationInsights } from "../personalization-insights";

// Mock the memory hooks
vi.mock("../../../../hooks/use-memory", () => ({
  useMemoryInsights: vi.fn(),
  useMemoryStats: vi.fn(),
  useUpdatePreferences: vi.fn(),
}));

import {
  useMemoryInsights,
  useMemoryStats,
  useUpdatePreferences,
} from "../../../../hooks/use-memory";

const MockUseMemoryInsights = vi.mocked(useMemoryInsights);
const MockUseMemoryStats = vi.mocked(useMemoryStats);
const MockUseUpdatePreferences = vi.mocked(useUpdatePreferences);

// Test wrapper factory
function createTestWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false, gcTime: 0, staleTime: 0 },
    },
  });

  return function TestWrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe("PersonalizationInsights", () => {
  const mockInsightsData = {
    insights: {
      budgetPatterns: {
        averageSpending: {
          accommodation: 350,
          activities: 85,
          dining: 120,
          flights: 950,
        },
        spendingTrends: [
          {
            category: "accommodation",
            percentageChange: 15,
            trend: "increasing" as const,
          },
          {
            category: "flights",
            percentageChange: 2,
            trend: "stable" as const,
          },
        ],
      },
      destinationPreferences: {
        topDestinations: [
          {
            destination: "Tokyo",
            lastVisit: "2024-03-15T10:00:00Z",
            satisfactionScore: 4.8,
            visits: 3,
          },
          {
            destination: "Paris",
            lastVisit: "2024-01-20T10:00:00Z",
            satisfactionScore: 4.5,
            visits: 2,
          },
        ],
      },
      recommendations: [
        {
          confidence: 0.92,
          reasoning: "Based on your preference for luxury and adventure",
          recommendation: "Consider luxury eco-lodges in Costa Rica",
          type: "destination",
        },
        {
          confidence: 0.85,
          reasoning: "Optimal timing for luxury accommodation availability",
          recommendation: "Book European trips 6-8 weeks in advance",
          type: "booking",
        },
      ],
      travelPersonality: {
        confidence: 0.89,
        description: "You enjoy luxury accommodations with adventurous activities",
        keyTraits: ["luxury", "adventure", "cultural", "premium"],
        type: "luxury_adventurer",
      },
    },
    metadata: {
      analysisDate: "2024-01-01T10:00:00Z",
      confidenceLevel: 0.87,
      dataCoverageMonths: 12,
    },
  };

  const mockStatsData = {
    memoryTypes: {
      accommodation: 68,
      activities: 35,
      destinations: 41,
      dining: 28,
      flights: 52,
    },
    totalMemories: 245,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    MockUseMemoryInsights.mockReturnValue({
      data: mockInsightsData,
      error: null,
      isError: false,
      isLoading: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useMemoryInsights>);
    MockUseMemoryStats.mockReturnValue({
      data: mockStatsData,
      isError: false,
      isLoading: false,
    } as unknown as ReturnType<typeof useMemoryStats>);
    MockUseUpdatePreferences.mockReturnValue({
      mutateAsync: vi.fn(),
    } as unknown as ReturnType<typeof useUpdatePreferences>);
  });

  describe("Rendering", () => {
    it("renders header with title and description", () => {
      render(<PersonalizationInsights userId="user-123" />, {
        wrapper: createTestWrapper(),
      });

      expect(screen.getByText("Personalization Insights")).toBeInTheDocument();
      expect(
        screen.getByText("AI-powered analysis of your travel patterns and preferences")
      ).toBeInTheDocument();
    });

    it("renders all navigation tabs", () => {
      render(<PersonalizationInsights userId="user-123" />, {
        wrapper: createTestWrapper(),
      });

      expect(screen.getByText("Overview")).toBeInTheDocument();
      expect(screen.getByText("Budget")).toBeInTheDocument();
      expect(screen.getByText("Destinations")).toBeInTheDocument();
      expect(screen.getByText("Recommendations")).toBeInTheDocument();
    });

    it("applies custom className", () => {
      const { container } = render(
        <PersonalizationInsights userId="user-123" className="custom-class" />,
        { wrapper: createTestWrapper() }
      );

      expect(container.firstChild).toHaveClass("custom-class");
    });
  });

  describe("Overview View", () => {
    it("displays travel personality information", () => {
      render(<PersonalizationInsights userId="user-123" />, {
        wrapper: createTestWrapper(),
      });

      expect(screen.getByText("luxury_adventurer")).toBeInTheDocument();
      expect(
        screen.getByText("You enjoy luxury accommodations with adventurous activities")
      ).toBeInTheDocument();
      expect(screen.getByText("89%")).toBeInTheDocument();
      expect(screen.getByText("luxury")).toBeInTheDocument();
      expect(screen.getByText("adventure")).toBeInTheDocument();
    });

    it("displays memory statistics", () => {
      render(<PersonalizationInsights userId="user-123" />, {
        wrapper: createTestWrapper(),
      });

      expect(screen.getByText("245")).toBeInTheDocument();
      expect(screen.getByText("68")).toBeInTheDocument();
      expect(screen.getByText("35")).toBeInTheDocument();
      expect(screen.getByText("41")).toBeInTheDocument();
    });

    it("displays top destinations", () => {
      render(<PersonalizationInsights userId="user-123" />, {
        wrapper: createTestWrapper(),
      });

      expect(screen.getByText("Tokyo")).toBeInTheDocument();
      expect(screen.getByText("Paris")).toBeInTheDocument();
      expect(screen.getByText("3 visits")).toBeInTheDocument();
      expect(screen.getByText("2 visits")).toBeInTheDocument();
      expect(screen.getByText("4.8/5")).toBeInTheDocument();
    });
  });

  describe("Budget View", () => {
    it("displays budget analysis when budget tab is clicked", () => {
      render(<PersonalizationInsights userId="user-123" />, {
        wrapper: createTestWrapper(),
      });

      fireEvent.click(screen.getByText("Budget"));

      expect(screen.getByText("Budget Analysis")).toBeInTheDocument();
      expect(screen.getByText("$350.00")).toBeInTheDocument();
      expect(screen.getByText("$950.00")).toBeInTheDocument();
      expect(screen.getByText("$120.00")).toBeInTheDocument();
      expect(screen.getByText("$85.00")).toBeInTheDocument();
    });

    it("displays spending trends", () => {
      render(<PersonalizationInsights userId="user-123" />, {
        wrapper: createTestWrapper(),
      });

      fireEvent.click(screen.getByText("Budget"));

      expect(screen.getByText("Spending Trends")).toBeInTheDocument();
      expect(screen.getByText("increasing trend")).toBeInTheDocument();
      expect(screen.getByText("stable trend")).toBeInTheDocument();
      expect(screen.getByText("+15%")).toBeInTheDocument();
      expect(screen.getByText("+2%")).toBeInTheDocument();
    });
  });

  describe("Recommendations View", () => {
    it("displays recommendations when recommendations tab is clicked and showRecommendations is true", () => {
      render(<PersonalizationInsights userId="user-123" showRecommendations={true} />, {
        wrapper: createTestWrapper(),
      });

      fireEvent.click(screen.getByText("Recommendations"));

      expect(screen.getByText("Personalized Recommendations")).toBeInTheDocument();
      expect(
        screen.getByText("Consider luxury eco-lodges in Costa Rica")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Book European trips 6-8 weeks in advance")
      ).toBeInTheDocument();
      expect(screen.getByText("92% confidence")).toBeInTheDocument();
      expect(screen.getByText("85% confidence")).toBeInTheDocument();
    });

    it("hides recommendations when showRecommendations is false", () => {
      render(<PersonalizationInsights userId="user-123" showRecommendations={false} />, {
        wrapper: createTestWrapper(),
      });

      fireEvent.click(screen.getByText("Recommendations"));

      expect(
        screen.queryByText("Consider luxury eco-lodges in Costa Rica")
      ).not.toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("displays loading skeleton when data is loading", () => {
      MockUseMemoryInsights.mockReturnValue({
        data: undefined,
        error: null,
        isError: false,
        isLoading: true,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useMemoryInsights>);
      MockUseMemoryStats.mockReturnValue({
        data: undefined,
        isError: false,
        isLoading: true,
      } as unknown as ReturnType<typeof useMemoryStats>);

      const { container } = render(<PersonalizationInsights userId="user-123" />, {
        wrapper: createTestWrapper(),
      });

      const pulses = container.querySelectorAll(".animate-pulse");
      expect(pulses.length).toBeGreaterThan(0);
    });
  });

  describe("Error State", () => {
    it("displays error message when insights fail to load", () => {
      MockUseMemoryInsights.mockReturnValue({
        data: undefined,
        error: new Error("Failed to load"),
        isError: true,
        isLoading: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useMemoryInsights>);

      render(<PersonalizationInsights userId="user-123" />, {
        wrapper: createTestWrapper(),
      });

      expect(
        screen.getByText(
          "Unable to load personalization insights. Please try refreshing the page."
        )
      ).toBeInTheDocument();
    });
  });

  describe("Metadata Display", () => {
    it("displays metadata information", () => {
      render(<PersonalizationInsights userId="user-123" />, {
        wrapper: createTestWrapper(),
      });

      expect(screen.getByText("Analysis based on 12 months of data")).toBeInTheDocument();
      expect(screen.getByText("Confidence: 87%")).toBeInTheDocument();
      expect(screen.getByText("Updated: 1/1/2024")).toBeInTheDocument();
    });
  });

  describe("Interactions", () => {
    it("calls refetch when refresh button is clicked", () => {
      const refetchSpy = vi.fn();
      MockUseMemoryInsights.mockReturnValue({
        data: mockInsightsData,
        error: null,
        isError: false,
        isLoading: false,
        refetch: refetchSpy,
      } as unknown as ReturnType<typeof useMemoryInsights>);

      render(<PersonalizationInsights userId="user-123" />, {
        wrapper: createTestWrapper(),
      });

      const refreshButton = screen.getByText("Refresh");
      fireEvent.click(refreshButton);

      expect(refetchSpy).toHaveBeenCalledTimes(1);
    });

    it("switches between views correctly", () => {
      render(<PersonalizationInsights userId="user-123" />, {
        wrapper: createTestWrapper(),
      });

      // Default overview
      expect(screen.getByText("luxury_adventurer")).toBeInTheDocument();

      // Switch to budget
      fireEvent.click(screen.getByText("Budget"));
      expect(screen.getByText("Budget Analysis")).toBeInTheDocument();

      // Switch back to overview
      fireEvent.click(screen.getByText("Overview"));
      expect(screen.getByText("luxury_adventurer")).toBeInTheDocument();
    });
  });

  describe("Edge Cases", () => {
    it("handles missing travel personality gracefully", () => {
      MockUseMemoryInsights.mockReturnValue({
        data: {
          insights: {
            budgetPatterns: mockInsightsData.insights.budgetPatterns,
            destinationPreferences: mockInsightsData.insights.destinationPreferences,
          },
          metadata: mockInsightsData.metadata,
        },
        error: null,
        isError: false,
        isLoading: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useMemoryInsights>);

      render(<PersonalizationInsights userId="user-123" />, {
        wrapper: createTestWrapper(),
      });

      expect(screen.getByText("Personalization Insights")).toBeInTheDocument();
      expect(screen.getByText("Memory Statistics")).toBeInTheDocument();
    });

    it("handles empty insights data", () => {
      MockUseMemoryInsights.mockReturnValue({
        data: {
          insights: {},
          metadata: null,
        },
        error: null,
        isError: false,
        isLoading: false,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof useMemoryInsights>);

      render(<PersonalizationInsights userId="user-123" />, {
        wrapper: createTestWrapper(),
      });

      expect(screen.getByText("Personalization Insights")).toBeInTheDocument();
    });
  });
});

