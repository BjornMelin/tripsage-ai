/**
 * Tests for MemoryContextPanel component
 */

import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, describe, it, expect, beforeEach } from "vitest";
import type { ReactNode } from "react";

import { MemoryContextPanel } from "../memory-context-panel";

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
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("MemoryContextPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockMemoryContext = {
    data: {
      memories: [
        {
          id: "mem-1",
          content: "User prefers luxury hotels",
          metadata: { category: "accommodation", preference: "luxury" },
          score: 0.95,
          created_at: "2024-01-01T10:00:00Z",
        },
        {
          id: "mem-2",
          content: "Budget typically $5000-10000",
          metadata: { category: "budget", amount: "5000-10000" },
          score: 0.9,
          created_at: "2024-01-01T09:00:00Z",
        },
      ],
      preferences: {
        accommodation: "luxury",
        budget: "high",
        destinations: ["Europe", "Asia"],
      },
      travel_patterns: {
        favorite_destinations: ["Paris", "Tokyo"],
        avg_trip_duration: 7,
        booking_lead_time: 30,
      },
    },
    isLoading: false,
    isError: false,
    error: null,
  };

  const mockMemoryInsights = {
    data: {
      travel_personality: "luxury_traveler",
      budget_patterns: {
        avg_hotel_budget: 300,
        avg_flight_budget: 800,
        budget_consistency: 0.85,
      },
      destination_preferences: {
        preferred_regions: ["Europe", "Asia"],
        climate_preference: "temperate",
        city_vs_nature: 0.7,
      },
      booking_behavior: {
        avg_lead_time: 45,
        flexible_dates: true,
        price_sensitivity: 0.6,
      },
      ai_recommendations: [
        "Consider luxury hotels in Kyoto for your next trip",
        "Book flights 6-8 weeks in advance for best prices",
      ],
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
    expect(screen.getByRole("tab", { name: /profile/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /insights/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /recent/i })).toBeInTheDocument();

    // Should show memory count
    expect(screen.getByText("150 memories")).toBeInTheDocument();
  });

  it("displays user preferences in profile tab", async () => {
    mockUseMemoryContext.mockReturnValue(mockMemoryContext);
    mockUseMemoryInsights.mockReturnValue(mockMemoryInsights);
    mockUseMemoryStats.mockReturnValue(mockMemoryStats);

    render(<MemoryContextPanel userId="user-123" />, {
      wrapper: createWrapper(),
    });

    // Profile tab should be active by default
    expect(screen.getByText("luxury")).toBeInTheDocument(); // accommodation preference
    expect(screen.getByText("high")).toBeInTheDocument(); // budget preference
    expect(screen.getByText("Europe")).toBeInTheDocument(); // destination
    expect(screen.getByText("Asia")).toBeInTheDocument(); // destination
  });

  it("displays travel insights when insights tab is clicked", async () => {
    mockUseMemoryContext.mockReturnValue(mockMemoryContext);
    mockUseMemoryInsights.mockReturnValue(mockMemoryInsights);
    mockUseMemoryStats.mockReturnValue(mockMemoryStats);

    render(<MemoryContextPanel userId="user-123" />, {
      wrapper: createWrapper(),
    });

    // Click insights tab
    fireEvent.click(screen.getByRole("tab", { name: /insights/i }));

    await waitFor(() => {
      expect(screen.getByText("luxury_traveler")).toBeInTheDocument();
      expect(screen.getByText("$300")).toBeInTheDocument(); // avg hotel budget
      expect(screen.getByText("$800")).toBeInTheDocument(); // avg flight budget
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
    fireEvent.click(screen.getByRole("tab", { name: /recent/i }));

    await waitFor(() => {
      expect(
        screen.getByText("User prefers luxury hotels")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Budget typically $5000-10000")
      ).toBeInTheDocument();
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

    expect(
      screen.getByText("Failed to load memory context")
    ).toBeInTheDocument();
  });

  it("handles empty memory data gracefully", () => {
    const emptyMemoryContext = {
      data: {
        memories: [],
        preferences: {},
        travel_patterns: {},
      },
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

    expect(screen.getByText("No memories yet")).toBeInTheDocument();
  });

  it("displays AI recommendations in insights tab", async () => {
    mockUseMemoryContext.mockReturnValue(mockMemoryContext);
    mockUseMemoryInsights.mockReturnValue(mockMemoryInsights);
    mockUseMemoryStats.mockReturnValue(mockMemoryStats);

    render(<MemoryContextPanel userId="user-123" />, {
      wrapper: createWrapper(),
    });

    // Click insights tab
    fireEvent.click(screen.getByRole("tab", { name: /insights/i }));

    await waitFor(() => {
      expect(
        screen.getByText("Consider luxury hotels in Kyoto for your next trip")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Book flights 6-8 weeks in advance for best prices")
      ).toBeInTheDocument();
    });
  });

  it("shows memory categories with counts", async () => {
    mockUseMemoryContext.mockReturnValue(mockMemoryContext);
    mockUseMemoryInsights.mockReturnValue(mockMemoryInsights);
    mockUseMemoryStats.mockReturnValue(mockMemoryStats);

    render(<MemoryContextPanel userId="user-123" />, {
      wrapper: createWrapper(),
    });

    // Should show category breakdown
    expect(screen.getByText("accommodation: 45")).toBeInTheDocument();
    expect(screen.getByText("flights: 38")).toBeInTheDocument();
    expect(screen.getByText("destinations: 32")).toBeInTheDocument();
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
    expect(mockUseMemoryInsights).toHaveBeenCalledWith("user-456");
    expect(mockUseMemoryStats).toHaveBeenCalledWith("user-456");
  });

  it("can be disabled via enabled prop", () => {
    mockUseMemoryContext.mockReturnValue(mockMemoryContext);
    mockUseMemoryInsights.mockReturnValue(mockMemoryInsights);
    mockUseMemoryStats.mockReturnValue(mockMemoryStats);

    render(<MemoryContextPanel userId="user-123" enabled={false} />, {
      wrapper: createWrapper(),
    });

    // Should call hooks with enabled=false
    expect(mockUseMemoryContext).toHaveBeenCalledWith("user-123", false);
  });

  it("handles memory score display", () => {
    mockUseMemoryContext.mockReturnValue(mockMemoryContext);
    mockUseMemoryInsights.mockReturnValue(mockMemoryInsights);
    mockUseMemoryStats.mockReturnValue(mockMemoryStats);

    render(<MemoryContextPanel userId="user-123" />, {
      wrapper: createWrapper(),
    });

    // Should show memory score as percentage
    expect(screen.getByText("87%")).toBeInTheDocument();
  });

  it("renders memory items with proper metadata", async () => {
    mockUseMemoryContext.mockReturnValue(mockMemoryContext);
    mockUseMemoryInsights.mockReturnValue(mockMemoryInsights);
    mockUseMemoryStats.mockReturnValue(mockMemoryStats);

    render(<MemoryContextPanel userId="user-123" />, {
      wrapper: createWrapper(),
    });

    // Click recent tab to see memories
    fireEvent.click(screen.getByRole("tab", { name: /recent/i }));

    await waitFor(() => {
      // Should show memory content and metadata
      expect(
        screen.getByText("User prefers luxury hotels")
      ).toBeInTheDocument();
      expect(screen.getByText("accommodation")).toBeInTheDocument(); // category badge
      expect(screen.getByText("95%")).toBeInTheDocument(); // confidence score
    });
  });
});
