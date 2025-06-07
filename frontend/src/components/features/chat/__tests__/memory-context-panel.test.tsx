/**
 * Tests for MemoryContextPanel component
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import MemoryContextPanel from "../memory-context-panel";

// Mock the memory hooks
vi.mock("../../../../hooks/use-memory", () => ({
  useMemoryContext: vi.fn(),
  useMemoryInsights: vi.fn(),
  useMemoryStats: vi.fn(),
}));

import {
  useMemoryContext,
  useMemoryInsights,
  useMemoryStats,
} from "../../../../hooks/use-memory";

const mockUseMemoryContext = useMemoryContext as any;
const mockUseMemoryInsights = useMemoryInsights as any;
const mockUseMemoryStats = useMemoryStats as any;

// Test wrapper with QueryClient
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function TestWrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe("MemoryContextPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockMemoryContext = {
    data: {
      context: {
        userPreferences: {
          destinations: ["Europe", "Asia"],
          budget_range: { min: 5000, max: 10000 },
          travel_style: "luxury",
          activities: ["museums", "fine dining", "cultural sites"],
        },
        recentMemories: [
          {
            id: "mem-1",
            content: "User prefers luxury hotels",
            type: "accommodation",
            createdAt: "2024-01-01T10:00:00Z",
          },
          {
            id: "mem-2",
            content: "Budget typically $5000-10000",
            type: "budget",
            createdAt: "2024-01-01T09:00:00Z",
          },
        ],
      },
      metadata: {
        totalMemories: 150,
        lastUpdated: "2024-01-01T10:00:00Z",
      },
    },
    isLoading: false,
    isError: false,
    error: null,
  };

  const mockMemoryInsights = {
    data: {
      insights: {
        travelPersonality: {
          type: "luxury_traveler",
          confidence: 0.89,
          description: "Prefers high-end accommodations and experiences",
          keyTraits: ["luxury", "comfort", "quality"],
        },
        budgetPatterns: {
          averageSpending: {
            accommodation: 300,
            flights: 800,
            activities: 200,
          },
        },
        destinationPreferences: {
          preferred_regions: ["Europe", "Asia"],
          climate_preference: "temperate",
          city_vs_nature: 0.7,
        },
        recommendations: [
          {
            type: "accommodation",
            recommendation: "Consider luxury hotels in Kyoto for your next trip",
            reasoning:
              "Based on your preference for luxury accommodations and interest in Asia",
            confidence: 0.85,
          },
          {
            type: "booking",
            recommendation: "Book flights 6-8 weeks in advance for best prices",
            reasoning:
              "Historical data shows this booking window offers optimal pricing",
            confidence: 0.92,
          },
        ],
      },
    },
    isLoading: false,
    isError: false,
  };

  const mockMemoryStats = {
    data: {
      total_memories: 150,
      memories_this_month: 12,
      top_categories: [
        { category: "accommodation", count: 45 },
        { category: "flights", count: 38 },
        { category: "destinations", count: 32 },
      ],
      memory_score: 0.87,
      last_updated: "2024-01-01T10:00:00Z",
    },
    isLoading: false,
    isError: false,
  };

  it("renders memory context panel with user data", async () => {
    mockUseMemoryContext.mockReturnValue(mockMemoryContext);
    mockUseMemoryInsights.mockReturnValue(mockMemoryInsights);
    mockUseMemoryStats.mockReturnValue(mockMemoryStats);

    render(<MemoryContextPanel userId="user-123" />, {
      wrapper: createWrapper(),
    });

    // Should show memory panel
    expect(screen.getByText("Memory Context")).toBeInTheDocument();

    // Should show tab navigation
    expect(screen.getByRole("button", { name: /profile/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /insights/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /recent/i })).toBeInTheDocument();

    // Should show memory count
    expect(screen.getByText("150")).toBeInTheDocument();
  });

  it("displays user preferences in profile tab", async () => {
    mockUseMemoryContext.mockReturnValue(mockMemoryContext);
    mockUseMemoryInsights.mockReturnValue(mockMemoryInsights);
    mockUseMemoryStats.mockReturnValue(mockMemoryStats);

    render(<MemoryContextPanel userId="user-123" />, {
      wrapper: createWrapper(),
    });

    // Profile tab should be active by default
    expect(screen.getByText("luxury")).toBeInTheDocument(); // travel style
    expect(screen.getByText("Europe")).toBeInTheDocument(); // destination
    expect(screen.getByText("Asia")).toBeInTheDocument(); // destination
    expect(screen.getByText("Budget Range")).toBeInTheDocument(); // budget section header
  });

  it("displays travel insights when insights tab is clicked", async () => {
    mockUseMemoryContext.mockReturnValue(mockMemoryContext);
    mockUseMemoryInsights.mockReturnValue(mockMemoryInsights);
    mockUseMemoryStats.mockReturnValue(mockMemoryStats);

    render(<MemoryContextPanel userId="user-123" />, {
      wrapper: createWrapper(),
    });

    // Click insights tab
    fireEvent.click(screen.getByRole("button", { name: /insights/i }));

    await waitFor(() => {
      expect(screen.getByText("luxury_traveler")).toBeInTheDocument();
      expect(screen.getByText("$300.00")).toBeInTheDocument(); // avg accommodation budget
      expect(screen.getByText("$800.00")).toBeInTheDocument(); // avg flight budget
    });
  });

  it("displays recent memories when recent tab is clicked", async () => {
    mockUseMemoryContext.mockReturnValue(mockMemoryContext);
    mockUseMemoryInsights.mockReturnValue(mockMemoryInsights);
    mockUseMemoryStats.mockReturnValue(mockMemoryStats);

    render(<MemoryContextPanel userId="user-123" />, {
      wrapper: createWrapper(),
    });

    // Click recent tab
    fireEvent.click(screen.getByRole("button", { name: /recent/i }));

    await waitFor(() => {
      expect(screen.getByText("User prefers luxury hotels")).toBeInTheDocument();
      expect(screen.getByText("Budget typically $5000-10000")).toBeInTheDocument();
      expect(screen.getByText("accommodation")).toBeInTheDocument(); // memory type badge
      expect(screen.getByText("budget")).toBeInTheDocument(); // memory type badge
    });
  });

  it("shows loading state when data is loading", () => {
    mockUseMemoryContext.mockReturnValue({
      ...mockMemoryContext,
      isLoading: true,
    });
    mockUseMemoryInsights.mockReturnValue({
      ...mockMemoryInsights,
      isLoading: true,
    });
    mockUseMemoryStats.mockReturnValue({ ...mockMemoryStats, isLoading: true });

    render(<MemoryContextPanel userId="user-123" />, {
      wrapper: createWrapper(),
    });

    // Should show loading skeletons
    expect(screen.getByTestId("memory-context-loading")).toBeInTheDocument();
  });

  it("shows error state when data fails to load", () => {
    mockUseMemoryContext.mockReturnValue({
      ...mockMemoryContext,
      isError: true,
      error: new Error("Failed to load memory context"),
    });
    mockUseMemoryInsights.mockReturnValue(mockMemoryInsights);
    mockUseMemoryStats.mockReturnValue(mockMemoryStats);

    render(<MemoryContextPanel userId="user-123" />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("Failed to load memory context")).toBeInTheDocument();
  });

  it("handles empty memory data gracefully", () => {
    const emptyMemoryContext = {
      data: null,
      isLoading: false,
      isError: false,
      error: null,
    };

    mockUseMemoryContext.mockReturnValue(emptyMemoryContext);
    mockUseMemoryInsights.mockReturnValue(mockMemoryInsights);
    mockUseMemoryStats.mockReturnValue(mockMemoryStats);

    render(<MemoryContextPanel userId="user-123" />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("No memory context available")).toBeInTheDocument();
  });

  it("displays AI recommendations in insights tab", async () => {
    mockUseMemoryContext.mockReturnValue(mockMemoryContext);
    mockUseMemoryInsights.mockReturnValue(mockMemoryInsights);
    mockUseMemoryStats.mockReturnValue(mockMemoryStats);

    render(<MemoryContextPanel userId="user-123" />, {
      wrapper: createWrapper(),
    });

    // Click insights tab
    fireEvent.click(screen.getByRole("button", { name: /insights/i }));

    await waitFor(() => {
      expect(
        screen.getByText("Consider luxury hotels in Kyoto for your next trip")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Book flights 6-8 weeks in advance for best prices")
      ).toBeInTheDocument();
    });
  });

  it("shows memory metadata", async () => {
    mockUseMemoryContext.mockReturnValue(mockMemoryContext);
    mockUseMemoryInsights.mockReturnValue(mockMemoryInsights);
    mockUseMemoryStats.mockReturnValue(mockMemoryStats);

    render(<MemoryContextPanel userId="user-123" />, {
      wrapper: createWrapper(),
    });

    // Should show metadata
    expect(screen.getByText("150")).toBeInTheDocument(); // total memories
    expect(screen.getByText("1/1/2024")).toBeInTheDocument(); // last updated date
  });

  it("updates when userId prop changes", async () => {
    mockUseMemoryContext.mockReturnValue(mockMemoryContext);
    mockUseMemoryInsights.mockReturnValue(mockMemoryInsights);
    mockUseMemoryStats.mockReturnValue(mockMemoryStats);

    const { rerender } = render(<MemoryContextPanel userId="user-123" />, {
      wrapper: createWrapper(),
    });

    // Change userId
    rerender(<MemoryContextPanel userId="user-456" />);

    // Should call hooks with new userId
    expect(mockUseMemoryContext).toHaveBeenCalledWith("user-456", true);
    expect(mockUseMemoryInsights).toHaveBeenCalledWith("user-456", true);
  });

  it("can be initialized with userId", () => {
    mockUseMemoryContext.mockReturnValue(mockMemoryContext);
    mockUseMemoryInsights.mockReturnValue(mockMemoryInsights);
    mockUseMemoryStats.mockReturnValue(mockMemoryStats);

    render(<MemoryContextPanel userId="user-123" />, {
      wrapper: createWrapper(),
    });

    // Should call hooks with userId and enabled=true
    expect(mockUseMemoryContext).toHaveBeenCalledWith("user-123", true);
  });

  it("handles confidence display in insights", async () => {
    mockUseMemoryContext.mockReturnValue(mockMemoryContext);
    mockUseMemoryInsights.mockReturnValue(mockMemoryInsights);
    mockUseMemoryStats.mockReturnValue(mockMemoryStats);

    render(<MemoryContextPanel userId="user-123" />, {
      wrapper: createWrapper(),
    });

    // Switch to insights tab
    fireEvent.click(screen.getByRole("button", { name: /insights/i }));

    await waitFor(() => {
      // Should show confidence scores
      expect(screen.getByText("89% confident")).toBeInTheDocument();
      expect(screen.getByText("85%")).toBeInTheDocument(); // recommendation confidence
    });
  });

  it("renders memory items with proper metadata", async () => {
    mockUseMemoryContext.mockReturnValue(mockMemoryContext);
    mockUseMemoryInsights.mockReturnValue(mockMemoryInsights);
    mockUseMemoryStats.mockReturnValue(mockMemoryStats);

    render(<MemoryContextPanel userId="user-123" />, {
      wrapper: createWrapper(),
    });

    // Click recent tab to see memories
    fireEvent.click(screen.getByRole("button", { name: /recent/i }));

    await waitFor(() => {
      // Should show memory content and metadata
      expect(screen.getByText("User prefers luxury hotels")).toBeInTheDocument();
      expect(screen.getByText("accommodation")).toBeInTheDocument(); // type badge
      expect(screen.getByText("budget")).toBeInTheDocument(); // type badge
    });
  });
});
