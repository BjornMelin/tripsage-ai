import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Deal, DealType } from "@/lib/schemas/deals";
import { useDealAlerts, useDeals, useFeaturedDeals, useSavedDeals } from "../use-deals";

// Mock current timestamp for consistent testing
const MOCK_TIMESTAMP = "2025-05-20T12:00:00.000Z";
vi.spyOn(Date.prototype, "toISOString").mockReturnValue(MOCK_TIMESTAMP);

// Sample deal data
const SAMPLE_DEALS = [
  {
    createdAt: "2025-05-01T00:00:00.000Z",
    currency: "USD",
    description: "Great deal on round-trip flights to Paris",
    destination: "Paris",
    discountPercentage: 50,
    expiryDate: "2025-06-01T00:00:00.000Z",
    featured: true,
    id: "deal1",
    imageUrl: "https://example.com/images/paris.jpg",
    origin: "New York",
    originalPrice: 599.99,
    price: 299.99,
    provider: "AirlineCo",
    tags: ["europe", "summer", "flight-deal"],
    title: "Cheap Flight to Paris",
    type: "flight" as DealType,
    updatedAt: "2025-05-01T00:00:00.000Z",
    url: "https://example.com/deal1",
    verified: true,
  },
  {
    createdAt: "2025-05-02T00:00:00.000Z",
    currency: "USD",
    description: "Discounted stay at 5-star hotel in Rome",
    destination: "Rome",
    discountPercentage: 50,
    expiryDate: "2025-06-15T00:00:00.000Z",
    featured: false,
    id: "deal2",
    originalPrice: 300,
    price: 150,
    provider: "HotelCo",
    title: "Luxury Hotel in Rome",
    type: "accommodation" as DealType,
    updatedAt: "2025-05-02T00:00:00.000Z",
    url: "https://example.com/deal2",
    verified: true,
  },
  {
    createdAt: "2025-05-03T00:00:00.000Z",
    currency: "USD",
    description: "All-inclusive package to Barcelona",
    destination: "Barcelona",
    discountPercentage: 40,
    expiryDate: "2025-07-01T00:00:00.000Z",
    featured: false,
    id: "deal3",
    imageUrl: "https://example.com/images/barcelona.jpg",
    origin: "London",
    originalPrice: 1499,
    price: 899,
    provider: "TravelCo",
    title: "Barcelona Vacation Package",
    type: "package" as DealType,
    updatedAt: "2025-05-03T00:00:00.000Z",
    url: "https://example.com/deal3",
    verified: true,
  },
];

// Sample alert data
const SAMPLE_ALERTS = [
  {
    createdAt: "2025-05-01T00:00:00.000Z",
    dealType: "flight" as DealType,
    destination: "Paris",
    id: "alert1",
    isActive: true,
    maxPrice: 400,
    minDiscount: 30,
    notificationType: "email" as const,
    origin: "New York",
    updatedAt: "2025-05-01T00:00:00.000Z",
    userId: "user1",
  },
  {
    createdAt: "2025-05-02T00:00:00.000Z",
    dealType: "accommodation" as DealType,
    destination: "Rome",
    id: "alert2",
    isActive: false,
    minDiscount: 25,
    notificationType: "both" as const,
    updatedAt: "2025-05-02T00:00:00.000Z",
    userId: "user1",
  },
];

// Create mock store state
const CREATE_MOCK_STORE = () => {
  const deals = SAMPLE_DEALS.reduce(
    (acc, deal) => {
      acc[deal.id] = deal;
      return acc;
    },
    {} as Record<string, Deal>
  );

  return {
    addAlert: vi.fn(),
    addDeal: vi.fn(),
    addToFeaturedDeals: vi.fn(),
    addToRecentlyViewed: vi.fn(),
    addToSavedDeals: vi.fn(),
    alerts: SAMPLE_ALERTS,
    clearFilters: vi.fn(),
    clearRecentlyViewed: vi.fn(),
    deals,
    featuredDeals: [SAMPLE_DEALS[0].id],
    filters: undefined,
    getAlertById: vi.fn((id: string) => SAMPLE_ALERTS.find((a) => a.id === id)),
    getDealById: vi.fn((id: string) => deals[id]),
    getDealsStats: vi.fn(() => ({
      averageDiscount: 46.67,
      byType: {
        accommodation: 1,
        flight: 1,
        package: 1,
      },
      totalCount: 3,
      totalSavings: 900.99,
    })),
    getFeaturedDeals: vi.fn(() => [SAMPLE_DEALS[0]]),
    getFilteredDeals: vi.fn(() => SAMPLE_DEALS),
    getRecentlyViewedDeals: vi.fn(() => [SAMPLE_DEALS[0], SAMPLE_DEALS[2]]),
    getSavedDeals: vi.fn(() => [SAMPLE_DEALS[0], SAMPLE_DEALS[1]]),
    initialize: vi.fn(),
    isInitialized: true,
    lastUpdated: MOCK_TIMESTAMP,
    recentlyViewedDeals: [SAMPLE_DEALS[0].id, SAMPLE_DEALS[2].id],
    removeAlert: vi.fn(),
    removeDeal: vi.fn(),
    removeFromFeaturedDeals: vi.fn(),
    removeFromSavedDeals: vi.fn(),
    reset: vi.fn(),
    savedDeals: [SAMPLE_DEALS[0].id, SAMPLE_DEALS[1].id],
    setFilters: vi.fn(),
    toggleAlertActive: vi.fn(),
    updateAlert: vi.fn(),
    updateDeal: vi.fn(),
  };
};

// Mock the deals store
const MOCK_STORE = CREATE_MOCK_STORE();
vi.mock("@/stores/deals-store", () => ({
  useDealsStore: vi.fn(() => MOCK_STORE),
}));

describe("useDeals Hook", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset filters for each test
    MOCK_STORE.filters = undefined;
    MOCK_STORE.getFilteredDeals.mockReturnValue(SAMPLE_DEALS);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should initialize the store when mounted", () => {
    const { result: _result } = renderHook<ReturnType<typeof useDeals>, void>(() =>
      useDeals()
    );

    // Check initialization was called
    expect(MOCK_STORE.isInitialized).toBe(true);
  });

  it("should provide access to all deals", () => {
    const { result } = renderHook<ReturnType<typeof useDeals>, void>(() => useDeals());

    expect(result.current.allDeals).toHaveLength(3);
    expect(result.current.allDeals.map((d) => d.id)).toContain(SAMPLE_DEALS[0].id);
    expect(result.current.allDeals.map((d) => d.id)).toContain(SAMPLE_DEALS[1].id);
    expect(result.current.allDeals.map((d) => d.id)).toContain(SAMPLE_DEALS[2].id);
  });

  it("should provide access to featured deals", () => {
    const { result } = renderHook<ReturnType<typeof useDeals>, void>(() => useDeals());

    expect(result.current.featuredDeals).toHaveLength(1);
    expect(result.current.featuredDeals[0].id).toBe(SAMPLE_DEALS[0].id);
  });

  it("should provide access to saved deals", () => {
    const { result } = renderHook<ReturnType<typeof useDeals>, void>(() => useDeals());

    expect(result.current.savedDeals).toHaveLength(2);
    expect(result.current.savedDeals.map((d) => d.id)).toContain(SAMPLE_DEALS[0].id);
    expect(result.current.savedDeals.map((d) => d.id)).toContain(SAMPLE_DEALS[1].id);
  });

  it("should provide access to recently viewed deals", () => {
    const { result } = renderHook<ReturnType<typeof useDeals>, void>(() => useDeals());

    expect(result.current.recentlyViewedDeals).toHaveLength(2);
    expect(result.current.recentlyViewedDeals.map((d) => d.id)).toContain(
      SAMPLE_DEALS[0].id
    );
    expect(result.current.recentlyViewedDeals.map((d) => d.id)).toContain(
      SAMPLE_DEALS[2].id
    );
  });

  it("should provide deal stats", () => {
    const { result } = renderHook<ReturnType<typeof useDeals>, void>(() => useDeals());

    expect(result.current.dealStats.totalCount).toBe(3);
    expect(result.current.dealStats.byType).toEqual({
      accommodation: 1,
      flight: 1,
      package: 1,
    });
  });

  it("should check if a deal is saved", () => {
    const { result } = renderHook<ReturnType<typeof useDeals>, void>(() => useDeals());

    expect(result.current.isDealSaved(SAMPLE_DEALS[0].id)).toBe(true);
    expect(result.current.isDealSaved(SAMPLE_DEALS[2].id)).toBe(false);
  });

  it("should check if a deal is featured", () => {
    const { result } = renderHook<ReturnType<typeof useDeals>, void>(() => useDeals());

    expect(result.current.isDealFeatured(SAMPLE_DEALS[0].id)).toBe(true);
    expect(result.current.isDealFeatured(SAMPLE_DEALS[1].id)).toBe(false);
  });

  it("should filter deals by type", () => {
    const { result } = renderHook<ReturnType<typeof useDeals>, void>(() => useDeals());

    // Mock the filtered results
    MOCK_STORE.getFilteredDeals.mockReturnValue([SAMPLE_DEALS[0]]);

    act(() => {
      result.current.filterByType("flight");
    });

    expect(MOCK_STORE.setFilters).toHaveBeenCalledWith({
      types: ["flight"],
    });
  });

  it("should filter deals by destination", () => {
    const { result } = renderHook<ReturnType<typeof useDeals>, void>(() => useDeals());

    // Mock the filtered results
    MOCK_STORE.getFilteredDeals.mockReturnValue([SAMPLE_DEALS[1]]);

    act(() => {
      result.current.filterByDestination("Rome");
    });

    expect(MOCK_STORE.setFilters).toHaveBeenCalledWith({
      destinations: ["Rome"],
    });
  });

  it("should clear filters", () => {
    const { result } = renderHook<ReturnType<typeof useDeals>, void>(() => useDeals());

    act(() => {
      result.current.clearFilters();
    });

    expect(MOCK_STORE.clearFilters).toHaveBeenCalled();
  });

  it("should sort deals by discount", () => {
    const { result } = renderHook<ReturnType<typeof useDeals>, void>(() => useDeals());

    const sortedDeals = result.current.sortDeals(
      result.current.allDeals,
      "discount",
      "desc"
    );

    expect(sortedDeals[0].id).toBe(SAMPLE_DEALS[0].id); // 50% discount
    expect(sortedDeals[1].id).toBe(SAMPLE_DEALS[1].id); // 50% discount
    expect(sortedDeals[2].id).toBe(SAMPLE_DEALS[2].id); // 40% discount
  });

  it("should sort deals by price", () => {
    const { result } = renderHook<ReturnType<typeof useDeals>, void>(() => useDeals());

    const sortedDeals = result.current.sortDeals(
      result.current.allDeals,
      "price",
      "asc"
    );

    expect(sortedDeals[0].id).toBe(SAMPLE_DEALS[1].id); // $150
    expect(sortedDeals[1].id).toBe(SAMPLE_DEALS[0].id); // $299.99
    expect(sortedDeals[2].id).toBe(SAMPLE_DEALS[2].id); // $899
  });

  it("should group deals by destination", () => {
    const { result } = renderHook<ReturnType<typeof useDeals>, void>(() => useDeals());

    expect(Object.keys(result.current.dealsByDestination)).toHaveLength(3);
    expect(result.current.dealsByDestination.Paris).toHaveLength(1);
    expect(result.current.dealsByDestination.Rome).toHaveLength(1);
    expect(result.current.dealsByDestination.Barcelona).toHaveLength(1);
  });

  it("should group deals by type", () => {
    const { result } = renderHook<ReturnType<typeof useDeals>, void>(() => useDeals());

    expect(Object.keys(result.current.dealsByType)).toHaveLength(3);
    expect(result.current.dealsByType.flight).toHaveLength(1);
    expect(result.current.dealsByType.accommodation).toHaveLength(1);
    expect(result.current.dealsByType.package).toHaveLength(1);
  });

  it("should provide unique destinations", () => {
    const { result } = renderHook<ReturnType<typeof useDeals>, void>(() => useDeals());

    expect(result.current.uniqueDestinations).toHaveLength(3);
    expect(result.current.uniqueDestinations).toContain("Paris");
    expect(result.current.uniqueDestinations).toContain("Rome");
    expect(result.current.uniqueDestinations).toContain("Barcelona");
  });

  it("should provide unique providers", () => {
    const { result } = renderHook<ReturnType<typeof useDeals>, void>(() => useDeals());

    expect(result.current.uniqueProviders).toHaveLength(3);
    expect(result.current.uniqueProviders).toContain("AirlineCo");
    expect(result.current.uniqueProviders).toContain("HotelCo");
    expect(result.current.uniqueProviders).toContain("TravelCo");
  });
});

describe("useDealAlerts Hook", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset alerts in mock
    MOCK_STORE.alerts = SAMPLE_ALERTS;
  });

  it("should provide access to all alerts", () => {
    const { result } = renderHook<ReturnType<typeof useDealAlerts>, void>(() =>
      useDealAlerts()
    );

    expect(result.current.alerts).toHaveLength(2);
    expect(result.current.alerts.map((a) => a.id)).toContain(SAMPLE_ALERTS[0].id);
    expect(result.current.alerts.map((a) => a.id)).toContain(SAMPLE_ALERTS[1].id);
  });

  it("should provide access to active alerts", () => {
    const { result } = renderHook<ReturnType<typeof useDealAlerts>, void>(() =>
      useDealAlerts()
    );

    expect(result.current.activeAlerts).toHaveLength(1);
    expect(result.current.activeAlerts[0].id).toBe(SAMPLE_ALERTS[0].id);
  });

  it("should group alerts by type", () => {
    const { result } = renderHook<ReturnType<typeof useDealAlerts>, void>(() =>
      useDealAlerts()
    );

    expect(Object.keys(result.current.alertsByType)).toHaveLength(2);
    expect(result.current.alertsByType.flight).toHaveLength(1);
    expect(result.current.alertsByType.accommodation).toHaveLength(1);
  });

  it("should toggle alert active state", () => {
    const { result } = renderHook(() => useDealAlerts());

    act(() => {
      result.current.toggleAlertActive(SAMPLE_ALERTS[0].id);
    });

    expect(MOCK_STORE.toggleAlertActive).toHaveBeenCalledWith(SAMPLE_ALERTS[0].id);
  });
});

describe("useFeaturedDeals Hook", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset featured deals in mock
    MOCK_STORE.featuredDeals = [SAMPLE_DEALS[0].id];
    MOCK_STORE.getFeaturedDeals.mockReturnValue([SAMPLE_DEALS[0]]);
  });

  it("should provide access to featured deals", () => {
    const { result } = renderHook<ReturnType<typeof useFeaturedDeals>, void>(() =>
      useFeaturedDeals()
    );

    expect(result.current.featuredDeals).toHaveLength(1);
    expect(result.current.featuredDeals[0].id).toBe(SAMPLE_DEALS[0].id);
  });

  it("should provide sorted featured deals", () => {
    const { result } = renderHook<ReturnType<typeof useFeaturedDeals>, void>(() =>
      useFeaturedDeals()
    );

    expect(result.current.sortedByDiscount).toHaveLength(1);
    expect(result.current.sortedByDiscount[0].id).toBe(SAMPLE_DEALS[0].id);
  });

  it("should provide top deals", () => {
    const { result } = renderHook<ReturnType<typeof useFeaturedDeals>, void>(() =>
      useFeaturedDeals()
    );

    expect(result.current.topDeals).toHaveLength(1);
    expect(result.current.topDeals[0].id).toBe(SAMPLE_DEALS[0].id);
  });

  it("should toggle featured status", () => {
    const { result } = renderHook<ReturnType<typeof useFeaturedDeals>, void>(() =>
      useFeaturedDeals()
    );

    // Initially featured
    expect(result.current.isDealFeatured(SAMPLE_DEALS[0].id)).toBe(true);

    // Remove from featured
    act(() => {
      result.current.toggleFeatured(SAMPLE_DEALS[0].id);
    });

    expect(MOCK_STORE.removeFromFeaturedDeals).toHaveBeenCalledWith(SAMPLE_DEALS[0].id);

    // Mock state update
    MOCK_STORE.featuredDeals = [];
    MOCK_STORE.getFeaturedDeals.mockReturnValue([]);

    // Add back to featured
    act(() => {
      result.current.toggleFeatured(SAMPLE_DEALS[1].id);
    });

    expect(MOCK_STORE.addToFeaturedDeals).toHaveBeenCalledWith(SAMPLE_DEALS[1].id);
  });
});

describe("useSavedDeals Hook", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset saved deals in mock
    MOCK_STORE.savedDeals = [SAMPLE_DEALS[0].id, SAMPLE_DEALS[1].id];
    MOCK_STORE.getSavedDeals.mockReturnValue([SAMPLE_DEALS[0], SAMPLE_DEALS[1]]);
  });

  it("should provide access to saved deals", () => {
    const { result } = renderHook<ReturnType<typeof useSavedDeals>, void>(() =>
      useSavedDeals()
    );

    expect(result.current.savedDeals).toHaveLength(2);
    expect(result.current.savedDeals.map((d) => d.id)).toContain(SAMPLE_DEALS[0].id);
    expect(result.current.savedDeals.map((d) => d.id)).toContain(SAMPLE_DEALS[1].id);
  });

  it("should provide sorted saved deals", () => {
    const { result } = renderHook<ReturnType<typeof useSavedDeals>, void>(() =>
      useSavedDeals()
    );

    // Deals are sorted by expiry date, so the closer date should be first
    expect(result.current.sortedByExpiry).toHaveLength(2);
    expect(result.current.sortedByExpiry[0].id).toBe(SAMPLE_DEALS[0].id); // Expires on June 1
    expect(result.current.sortedByExpiry[1].id).toBe(SAMPLE_DEALS[1].id); // Expires on June 15
  });

  it("should toggle saved status", () => {
    const { result } = renderHook<ReturnType<typeof useSavedDeals>, void>(() =>
      useSavedDeals()
    );

    // Initially saved
    expect(result.current.isDealSaved(SAMPLE_DEALS[0].id)).toBe(true);

    // Remove from saved
    act(() => {
      result.current.toggleSaved(SAMPLE_DEALS[0].id);
    });

    expect(MOCK_STORE.removeFromSavedDeals).toHaveBeenCalledWith(SAMPLE_DEALS[0].id);

    // Mock state update
    MOCK_STORE.savedDeals = [SAMPLE_DEALS[1].id];
    MOCK_STORE.getSavedDeals.mockReturnValue([SAMPLE_DEALS[1]]);

    // Add back to saved
    act(() => {
      result.current.toggleSaved(SAMPLE_DEALS[2].id);
    });

    expect(MOCK_STORE.addToSavedDeals).toHaveBeenCalledWith(SAMPLE_DEALS[2].id);
  });
});
