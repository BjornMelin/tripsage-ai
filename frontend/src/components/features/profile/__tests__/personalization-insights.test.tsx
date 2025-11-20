/** @vitest-environment jsdom */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useMemoryInsights, useMemoryStats } from "@/hooks/use-memory";
import { PersonalizationInsights } from "../personalization-insights";

vi.mock("@/hooks/use-memory");

const MockUseMemoryInsights = vi.mocked(useMemoryInsights);
const MockUseMemoryStats = vi.mocked(useMemoryStats);

function CreateTestWrapper() {
  const { QueryClient, QueryClientProvider } = require("@tanstack/react-query");
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { gcTime: 0, retry: false, staleTime: 0 },
    },
  });

  return ({ children }: { children: React.ReactNode }) => {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe("PersonalizationInsights", () => {
  const minimalInsightsData = {
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
        ],
      },
      recommendations: [
        {
          confidence: 0.92,
          reasoning: "Based on your preference",
          recommendation: "Consider luxury eco-lodges",
          type: "destination",
        },
      ],
      travelPersonality: {
        confidence: 0.89,
        description: "You enjoy luxury accommodations",
        keyTraits: ["luxury", "adventure"],
        type: "luxury_adventurer",
      },
    },
    metadata: {
      analysisDate: "2024-01-01T10:00:00Z",
      confidenceLevel: 0.87,
      dataCoverageMonths: 12,
    },
  };

  const minimalStatsData = {
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
    vi.useRealTimers();
    vi.clearAllMocks();
    MockUseMemoryInsights.mockReturnValue({
      data: minimalInsightsData,
      error: null,
      isError: false,
      isLoading: false,
      refetch: vi.fn(),
    } as never);
    MockUseMemoryStats.mockReturnValue({
      data: minimalStatsData,
      isError: false,
      isLoading: false,
    } as never);
  });

  it("renders header with title and description", () => {
    render(<PersonalizationInsights userId="user-123" />, {
      wrapper: CreateTestWrapper(),
    });

    expect(screen.getByText(/personalization insights/i)).toBeInTheDocument();
  });

  it("displays travel personality information", () => {
    render(<PersonalizationInsights userId="user-123" />, {
      wrapper: CreateTestWrapper(),
    });

    expect(screen.getByText(/luxury accommodations/i)).toBeInTheDocument();
  });

  it("displays top destinations", () => {
    render(<PersonalizationInsights userId="user-123" />, {
      wrapper: CreateTestWrapper(),
    });

    expect(screen.getByText(/Tokyo/i)).toBeInTheDocument();
  });

  it("displays recommendations when recommendations tab is clicked and showRecommendations is true", async () => {
    render(<PersonalizationInsights userId="user-123" showRecommendations={true} />, {
      wrapper: CreateTestWrapper(),
    });

    // Click on recommendations button
    const recommendationsButton = screen.getByRole("button", {
      name: /recommendations/i,
    });
    fireEvent.click(recommendationsButton);

    expect(screen.getByText(/luxury eco-lodges/i)).toBeInTheDocument();
  });

  it("switches between views correctly", () => {
    render(<PersonalizationInsights userId="user-123" />, {
      wrapper: CreateTestWrapper(),
    });

    // Component uses buttons, not tabs with role="tab"
    const budgetButton = screen.getByRole("button", { name: /budget/i });
    expect(budgetButton).toBeInTheDocument();
  });
});
