/**
 * Tests for PersonalizationInsights component
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import type { ReactNode } from 'react';

import { PersonalizationInsights } from '../personalization-insights';

// Mock the memory hooks
vi.mock('../../../lib/hooks/use-memory', () => ({
  useMemoryInsights: vi.fn(),
  useMemoryStats: vi.fn(),
  useMemoryContext: vi.fn(),
}));

import { useMemoryInsights, useMemoryStats, useMemoryContext } from '../../../lib/hooks/use-memory';

const mockUseMemoryInsights = useMemoryInsights as any;
const mockUseMemoryStats = useMemoryStats as any;
const mockUseMemoryContext = useMemoryContext as any;

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
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
}

describe('PersonalizationInsights', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockInsightsData = {
    data: {
      travel_personality: 'luxury_adventurer',
      budget_patterns: {
        avg_hotel_budget: 350,
        avg_flight_budget: 950,
        budget_consistency: 0.78,
        seasonal_variation: 0.15,
      },
      destination_preferences: {
        preferred_regions: ['Europe', 'Southeast Asia', 'North America'],
        climate_preference: 'temperate',
        city_vs_nature: 0.65,
        cultural_interest: 0.85,
      },
      booking_behavior: {
        avg_lead_time: 42,
        flexible_dates: true,
        price_sensitivity: 0.45,
        loyalty_program_usage: 0.8,
      },
      travel_patterns: {
        trip_frequency: 8,
        avg_duration: 9,
        preferred_season: 'spring',
        group_vs_solo: 0.3,
      },
      ai_recommendations: [
        'Consider luxury eco-lodges in Costa Rica for your adventurous side',
        'Book European trips 6-8 weeks in advance for best luxury options',
        'Explore cultural experiences in Japan during cherry blossom season',
      ],
    },
    isLoading: false,
    isError: false,
    error: null,
  };

  const mockStatsData = {
    data: {
      total_memories: 245,
      memories_this_month: 18,
      top_categories: [
        { category: 'accommodation', count: 68 },
        { category: 'flights', count: 52 },
        { category: 'destinations', count: 41 },
        { category: 'activities', count: 35 },
        { category: 'dining', count: 28 },
      ],
      memory_score: 0.91,
      learning_progress: 0.73,
      last_updated: '2024-01-01T10:00:00Z',
    },
    isLoading: false,
    isError: false,
  };

  const mockContextData = {
    data: {
      preferences: {
        accommodation: 'luxury',
        budget: 'high',
        destinations: ['Europe', 'Asia'],
        travel_style: 'adventure',
      },
      travel_patterns: {
        favorite_destinations: ['Paris', 'Tokyo', 'Bali'],
        avg_trip_duration: 9,
        booking_lead_time: 42,
      },
    },
    isLoading: false,
    isError: false,
  };

  it('renders personalization insights dashboard', async () => {
    mockUseMemoryInsights.mockReturnValue(mockInsightsData);
    mockUseMemoryStats.mockReturnValue(mockStatsData);
    mockUseMemoryContext.mockReturnValue(mockContextData);

    render(
      <PersonalizationInsights userId="user-123" />,
      { wrapper: createWrapper() }
    );

    // Should show main title
    expect(screen.getByText('Travel Analytics')).toBeInTheDocument();
    
    // Should show travel personality
    expect(screen.getByText('luxury_adventurer')).toBeInTheDocument();
    
    // Should show memory statistics
    expect(screen.getByText('245')).toBeInTheDocument(); // total memories
    expect(screen.getByText('91%')).toBeInTheDocument(); // memory score
  });

  it('displays budget patterns correctly', async () => {
    mockUseMemoryInsights.mockReturnValue(mockInsightsData);
    mockUseMemoryStats.mockReturnValue(mockStatsData);
    mockUseMemoryContext.mockReturnValue(mockContextData);

    render(
      <PersonalizationInsights userId="user-123" />,
      { wrapper: createWrapper() }
    );

    // Click budget view
    fireEvent.click(screen.getByText('Budget'));

    await waitFor(() => {
      expect(screen.getByText('$350')).toBeInTheDocument(); // avg hotel budget
      expect(screen.getByText('$950')).toBeInTheDocument(); // avg flight budget
      expect(screen.getByText('78%')).toBeInTheDocument(); // budget consistency
    });
  });

  it('shows destination preferences in destinations view', async () => {
    mockUseMemoryInsights.mockReturnValue(mockInsightsData);
    mockUseMemoryStats.mockReturnValue(mockStatsData);
    mockUseMemoryContext.mockReturnValue(mockContextData);

    render(
      <PersonalizationInsights userId="user-123" />,
      { wrapper: createWrapper() }
    );

    // Click destinations view
    fireEvent.click(screen.getByText('Destinations'));

    await waitFor(() => {
      expect(screen.getByText('Europe')).toBeInTheDocument();
      expect(screen.getByText('Southeast Asia')).toBeInTheDocument();
      expect(screen.getByText('North America')).toBeInTheDocument();
      expect(screen.getByText('temperate')).toBeInTheDocument(); // climate preference
    });
  });

  it('displays AI recommendations in recommendations view', async () => {
    mockUseMemoryInsights.mockReturnValue(mockInsightsData);
    mockUseMemoryStats.mockReturnValue(mockStatsData);
    mockUseMemoryContext.mockReturnValue(mockContextData);

    render(
      <PersonalizationInsights userId="user-123" />,
      { wrapper: createWrapper() }
    );

    // Click recommendations view
    fireEvent.click(screen.getByText('Recommendations'));

    await waitFor(() => {
      expect(screen.getByText('Consider luxury eco-lodges in Costa Rica for your adventurous side')).toBeInTheDocument();
      expect(screen.getByText('Book European trips 6-8 weeks in advance for best luxury options')).toBeInTheDocument();
      expect(screen.getByText('Explore cultural experiences in Japan during cherry blossom season')).toBeInTheDocument();
    });
  });

  it('shows loading state when data is loading', () => {
    mockUseMemoryInsights.mockReturnValue({ ...mockInsightsData, isLoading: true });
    mockUseMemoryStats.mockReturnValue({ ...mockStatsData, isLoading: true });
    mockUseMemoryContext.mockReturnValue({ ...mockContextData, isLoading: true });

    render(
      <PersonalizationInsights userId="user-123" />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByTestId('insights-loading')).toBeInTheDocument();
  });

  it('shows error state when data fails to load', () => {
    mockUseMemoryInsights.mockReturnValue({
      ...mockInsightsData,
      isError: true,
      error: new Error('Failed to load insights'),
    });
    mockUseMemoryStats.mockReturnValue(mockStatsData);
    mockUseMemoryContext.mockReturnValue(mockContextData);

    render(
      <PersonalizationInsights userId="user-123" />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText('Failed to load insights')).toBeInTheDocument();
  });

  it('handles empty insights data gracefully', () => {
    const emptyInsights = {
      data: {
        travel_personality: null,
        budget_patterns: {},
        destination_preferences: {},
        booking_behavior: {},
        ai_recommendations: [],
      },
      isLoading: false,
      isError: false,
      error: null,
    };

    mockUseMemoryInsights.mockReturnValue(emptyInsights);
    mockUseMemoryStats.mockReturnValue(mockStatsData);
    mockUseMemoryContext.mockReturnValue(mockContextData);

    render(
      <PersonalizationInsights userId="user-123" />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText('Not enough data yet')).toBeInTheDocument();
  });

  it('displays category breakdown chart', async () => {
    mockUseMemoryInsights.mockReturnValue(mockInsightsData);
    mockUseMemoryStats.mockReturnValue(mockStatsData);
    mockUseMemoryContext.mockReturnValue(mockContextData);

    render(
      <PersonalizationInsights userId="user-123" />,
      { wrapper: createWrapper() }
    );

    // Should show top categories
    expect(screen.getByText('accommodation: 68')).toBeInTheDocument();
    expect(screen.getByText('flights: 52')).toBeInTheDocument();
    expect(screen.getByText('destinations: 41')).toBeInTheDocument();
  });

  it('shows travel patterns and frequency', async () => {
    mockUseMemoryInsights.mockReturnValue(mockInsightsData);
    mockUseMemoryStats.mockReturnValue(mockStatsData);
    mockUseMemoryContext.mockReturnValue(mockContextData);

    render(
      <PersonalizationInsights userId="user-123" />,
      { wrapper: createWrapper() }
    );

    // Should show travel frequency and patterns
    expect(screen.getByText('8 trips/year')).toBeInTheDocument();
    expect(screen.getByText('9 days avg')).toBeInTheDocument();
    expect(screen.getByText('spring')).toBeInTheDocument(); // preferred season
  });

  it('displays booking behavior insights', async () => {
    mockUseMemoryInsights.mockReturnValue(mockInsightsData);
    mockUseMemoryStats.mockReturnValue(mockStatsData);
    mockUseMemoryContext.mockReturnValue(mockContextData);

    render(
      <PersonalizationInsights userId="user-123" />,
      { wrapper: createWrapper() }
    );

    // Should show booking behavior metrics
    expect(screen.getByText('42 days')).toBeInTheDocument(); // avg lead time
    expect(screen.getByText('Flexible dates')).toBeInTheDocument();
    expect(screen.getByText('45%')).toBeInTheDocument(); // price sensitivity
    expect(screen.getByText('80%')).toBeInTheDocument(); // loyalty program usage
  });

  it('handles view switching correctly', async () => {
    mockUseMemoryInsights.mockReturnValue(mockInsightsData);
    mockUseMemoryStats.mockReturnValue(mockStatsData);
    mockUseMemoryContext.mockReturnValue(mockContextData);

    render(
      <PersonalizationInsights userId="user-123" />,
      { wrapper: createWrapper() }
    );

    // Default overview view
    expect(screen.getByText('luxury_adventurer')).toBeInTheDocument();

    // Switch to budget view
    fireEvent.click(screen.getByText('Budget'));
    await waitFor(() => {
      expect(screen.getByText('Budget Patterns')).toBeInTheDocument();
    });

    // Switch to destinations view
    fireEvent.click(screen.getByText('Destinations'));
    await waitFor(() => {
      expect(screen.getByText('Preferred Regions')).toBeInTheDocument();
    });

    // Switch back to overview
    fireEvent.click(screen.getByText('Overview'));
    await waitFor(() => {
      expect(screen.getByText('luxury_adventurer')).toBeInTheDocument();
    });
  });

  it('shows learning progress indicator', () => {
    mockUseMemoryInsights.mockReturnValue(mockInsightsData);
    mockUseMemoryStats.mockReturnValue(mockStatsData);
    mockUseMemoryContext.mockReturnValue(mockContextData);

    render(
      <PersonalizationInsights userId="user-123" />,
      { wrapper: createWrapper() }
    );

    // Should show learning progress
    expect(screen.getByText('73%')).toBeInTheDocument(); // learning progress
    expect(screen.getByText('Learning Progress')).toBeInTheDocument();
  });

  it('updates when userId changes', async () => {
    mockUseMemoryInsights.mockReturnValue(mockInsightsData);
    mockUseMemoryStats.mockReturnValue(mockStatsData);
    mockUseMemoryContext.mockReturnValue(mockContextData);

    const { rerender } = render(
      <PersonalizationInsights userId="user-123" />,
      { wrapper: createWrapper() }
    );

    // Change userId
    rerender(
      <PersonalizationInsights userId="user-456" />
    );

    // Should call hooks with new userId
    expect(mockUseMemoryInsights).toHaveBeenCalledWith('user-456');
    expect(mockUseMemoryStats).toHaveBeenCalledWith('user-456');
    expect(mockUseMemoryContext).toHaveBeenCalledWith('user-456', true);
  });

  it('displays cultural interest and travel style preferences', () => {
    mockUseMemoryInsights.mockReturnValue(mockInsightsData);
    mockUseMemoryStats.mockReturnValue(mockStatsData);
    mockUseMemoryContext.mockReturnValue(mockContextData);

    render(
      <PersonalizationInsights userId="user-123" />,
      { wrapper: createWrapper() }
    );

    // Should show cultural interest level
    expect(screen.getByText('85%')).toBeInTheDocument(); // cultural interest
    
    // Should show city vs nature preference
    expect(screen.getByText('65%')).toBeInTheDocument(); // city vs nature (65% city)
  });

  it('shows seasonal and group travel preferences', () => {
    mockUseMemoryInsights.mockReturnValue(mockInsightsData);
    mockUseMemoryStats.mockReturnValue(mockStatsData);
    mockUseMemoryContext.mockReturnValue(mockContextData);

    render(
      <PersonalizationInsights userId="user-123" />,
      { wrapper: createWrapper() }
    );

    // Should show seasonal preference
    expect(screen.getByText('spring')).toBeInTheDocument();
    
    // Should show group vs solo travel (30% group, 70% solo)
    expect(screen.getByText('30%')).toBeInTheDocument(); // group travel
  });

  it('handles partial data gracefully', () => {
    const partialInsights = {
      data: {
        travel_personality: 'budget_explorer',
        budget_patterns: {
          avg_hotel_budget: 120,
        },
        destination_preferences: {},
        booking_behavior: {},
        ai_recommendations: ['Try budget hostels in Eastern Europe'],
      },
      isLoading: false,
      isError: false,
      error: null,
    };

    mockUseMemoryInsights.mockReturnValue(partialInsights);
    mockUseMemoryStats.mockReturnValue(mockStatsData);
    mockUseMemoryContext.mockReturnValue(mockContextData);

    render(
      <PersonalizationInsights userId="user-123" />,
      { wrapper: createWrapper() }
    );

    // Should show available data
    expect(screen.getByText('budget_explorer')).toBeInTheDocument();
    expect(screen.getByText('$120')).toBeInTheDocument();
    
    // Should handle missing data gracefully
    expect(screen.getByText('Try budget hostels in Eastern Europe')).toBeInTheDocument();
  });
});