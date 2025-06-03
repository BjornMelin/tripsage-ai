import { useDealsStore } from "@/stores/deals-store";
import type { DealType } from "@/types/deals";
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useDealAlerts, useDeals, useFeaturedDeals, useSavedDeals } from "../use-deals";

// Mock current timestamp for consistent testing
const mockTimestamp = "2025-05-20T12:00:00.000Z";
vi.spyOn(Date.prototype, "toISOString").mockReturnValue(mockTimestamp);

// Sample deal data
const sampleDeals = [
  {
    id: "deal1",
    type: "flight" as DealType,
    title: "Cheap Flight to Paris",
    description: "Great deal on round-trip flights to Paris",
    provider: "AirlineCo",
    url: "https://example.com/deal1",
    price: 299.99,
    originalPrice: 599.99,
    discountPercentage: 50,
    currency: "USD",
    destination: "Paris",
    origin: "New York",
    expiryDate: "2025-06-01T00:00:00.000Z",
    imageUrl: "https://example.com/images/paris.jpg",
    tags: ["europe", "summer", "flight-deal"],
    featured: true,
    verified: true,
    createdAt: "2025-05-01T00:00:00.000Z",
    updatedAt: "2025-05-01T00:00:00.000Z",
  },
  {
    id: "deal2",
    type: "accommodation" as DealType,
    title: "Luxury Hotel in Rome",
    description: "Discounted stay at 5-star hotel in Rome",
    provider: "HotelCo",
    url: "https://example.com/deal2",
    price: 150,
    originalPrice: 300,
    discountPercentage: 50,
    currency: "USD",
    destination: "Rome",
    expiryDate: "2025-06-15T00:00:00.000Z",
    featured: false,
    verified: true,
    createdAt: "2025-05-02T00:00:00.000Z",
    updatedAt: "2025-05-02T00:00:00.000Z",
  },
  {
    id: "deal3",
    type: "package" as DealType,
    title: "Barcelona Vacation Package",
    description: "All-inclusive package to Barcelona",
    provider: "TravelCo",
    url: "https://example.com/deal3",
    price: 899,
    originalPrice: 1499,
    discountPercentage: 40,
    currency: "USD",
    destination: "Barcelona",
    origin: "London",
    expiryDate: "2025-07-01T00:00:00.000Z",
    imageUrl: "https://example.com/images/barcelona.jpg",
    featured: false,
    verified: true,
    createdAt: "2025-05-03T00:00:00.000Z",
    updatedAt: "2025-05-03T00:00:00.000Z",
  },
];

// Sample alert data
const sampleAlerts = [
  {
    id: "alert1",
    userId: "user1",
    dealType: "flight" as DealType,
    origin: "New York",
    destination: "Paris",
    minDiscount: 30,
    maxPrice: 400,
    isActive: true,
    notificationType: "email" as const,
    createdAt: "2025-05-01T00:00:00.000Z",
    updatedAt: "2025-05-01T00:00:00.000Z",
  },
  {
    id: "alert2",
    userId: "user1",
    dealType: "accommodation" as DealType,
    destination: "Rome",
    minDiscount: 25,
    isActive: false,
    notificationType: "both" as const,
    createdAt: "2025-05-02T00:00:00.000Z",
    updatedAt: "2025-05-02T00:00:00.000Z",
  },
];

describe("useDeals Hook", () => {
  beforeEach(() => {
    // Reset store before each test
    const store = useDealsStore.getState();
    store.reset();

    // Add sample data
    sampleDeals.forEach((deal) => store.addDeal(deal));
    sampleAlerts.forEach((alert) => store.addAlert(alert));

    // Set up collections
    store.addToFeaturedDeals(sampleDeals[0].id);
    store.addToSavedDeals(sampleDeals[0].id);
    store.addToSavedDeals(sampleDeals[1].id);
    store.addToRecentlyViewed(sampleDeals[0].id);
    store.addToRecentlyViewed(sampleDeals[2].id);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should initialize the store when mounted", () => {
    const { result } = renderHook(() => useDeals());

    // Check initialization was called
    expect(useDealsStore.getState().isInitialized).toBe(true);
  });

  it("should provide access to all deals", () => {
    const { result } = renderHook(() => useDeals());

    expect(result.current.allDeals).toHaveLength(3);
    expect(result.current.allDeals.map((d) => d.id)).toContain(sampleDeals[0].id);
    expect(result.current.allDeals.map((d) => d.id)).toContain(sampleDeals[1].id);
    expect(result.current.allDeals.map((d) => d.id)).toContain(sampleDeals[2].id);
  });

  it("should provide access to featured deals", () => {
    const { result } = renderHook(() => useDeals());

    expect(result.current.featuredDeals).toHaveLength(1);
    expect(result.current.featuredDeals[0].id).toBe(sampleDeals[0].id);
  });

  it("should provide access to saved deals", () => {
    const { result } = renderHook(() => useDeals());

    expect(result.current.savedDeals).toHaveLength(2);
    expect(result.current.savedDeals.map((d) => d.id)).toContain(sampleDeals[0].id);
    expect(result.current.savedDeals.map((d) => d.id)).toContain(sampleDeals[1].id);
  });

  it("should provide access to recently viewed deals", () => {
    const { result } = renderHook(() => useDeals());

    expect(result.current.recentlyViewedDeals).toHaveLength(2);
    expect(result.current.recentlyViewedDeals.map((d) => d.id)).toContain(
      sampleDeals[0].id
    );
    expect(result.current.recentlyViewedDeals.map((d) => d.id)).toContain(
      sampleDeals[2].id
    );
  });

  it("should provide deal stats", () => {
    const { result } = renderHook(() => useDeals());

    expect(result.current.dealStats.totalCount).toBe(3);
    expect(result.current.dealStats.byType).toEqual({
      flight: 1,
      accommodation: 1,
      package: 1,
    });
  });

  it("should check if a deal is saved", () => {
    const { result } = renderHook(() => useDeals());

    expect(result.current.isDealSaved(sampleDeals[0].id)).toBe(true);
    expect(result.current.isDealSaved(sampleDeals[2].id)).toBe(false);
  });

  it("should check if a deal is featured", () => {
    const { result } = renderHook(() => useDeals());

    expect(result.current.isDealFeatured(sampleDeals[0].id)).toBe(true);
    expect(result.current.isDealFeatured(sampleDeals[1].id)).toBe(false);
  });

  it("should filter deals by type", () => {
    const { result } = renderHook(() => useDeals());

    act(() => {
      result.current.filterByType("flight");
    });

    expect(result.current.filteredDeals).toHaveLength(1);
    expect(result.current.filteredDeals[0].id).toBe(sampleDeals[0].id);
  });

  it("should filter deals by destination", () => {
    const { result } = renderHook(() => useDeals());

    act(() => {
      result.current.filterByDestination("Rome");
    });

    expect(result.current.filteredDeals).toHaveLength(1);
    expect(result.current.filteredDeals[0].id).toBe(sampleDeals[1].id);
  });

  it("should clear filters", () => {
    const { result } = renderHook(() => useDeals());

    act(() => {
      result.current.filterByType("flight");
    });

    expect(result.current.filteredDeals).toHaveLength(1);

    act(() => {
      result.current.clearFilters();
    });

    expect(result.current.filteredDeals).toHaveLength(3);
  });

  it("should sort deals by discount", () => {
    const { result } = renderHook(() => useDeals());

    const sortedDeals = result.current.sortDeals(
      result.current.allDeals,
      "discount",
      "desc"
    );

    expect(sortedDeals[0].id).toBe(sampleDeals[0].id); // 50% discount
    expect(sortedDeals[1].id).toBe(sampleDeals[1].id); // 50% discount
    expect(sortedDeals[2].id).toBe(sampleDeals[2].id); // 40% discount
  });

  it("should sort deals by price", () => {
    const { result } = renderHook(() => useDeals());

    const sortedDeals = result.current.sortDeals(
      result.current.allDeals,
      "price",
      "asc"
    );

    expect(sortedDeals[0].id).toBe(sampleDeals[1].id); // $150
    expect(sortedDeals[1].id).toBe(sampleDeals[0].id); // $299.99
    expect(sortedDeals[2].id).toBe(sampleDeals[2].id); // $899
  });

  it("should group deals by destination", () => {
    const { result } = renderHook(() => useDeals());

    expect(Object.keys(result.current.dealsByDestination)).toHaveLength(3);
    expect(result.current.dealsByDestination["Paris"]).toHaveLength(1);
    expect(result.current.dealsByDestination["Rome"]).toHaveLength(1);
    expect(result.current.dealsByDestination["Barcelona"]).toHaveLength(1);
  });

  it("should group deals by type", () => {
    const { result } = renderHook(() => useDeals());

    expect(Object.keys(result.current.dealsByType)).toHaveLength(3);
    expect(result.current.dealsByType["flight"]).toHaveLength(1);
    expect(result.current.dealsByType["accommodation"]).toHaveLength(1);
    expect(result.current.dealsByType["package"]).toHaveLength(1);
  });

  it("should provide unique destinations", () => {
    const { result } = renderHook(() => useDeals());

    expect(result.current.uniqueDestinations).toHaveLength(3);
    expect(result.current.uniqueDestinations).toContain("Paris");
    expect(result.current.uniqueDestinations).toContain("Rome");
    expect(result.current.uniqueDestinations).toContain("Barcelona");
  });

  it("should provide unique providers", () => {
    const { result } = renderHook(() => useDeals());

    expect(result.current.uniqueProviders).toHaveLength(3);
    expect(result.current.uniqueProviders).toContain("AirlineCo");
    expect(result.current.uniqueProviders).toContain("HotelCo");
    expect(result.current.uniqueProviders).toContain("TravelCo");
  });
});

describe("useDealAlerts Hook", () => {
  beforeEach(() => {
    // Reset store before each test
    const store = useDealsStore.getState();
    store.reset();

    // Add sample alerts
    sampleAlerts.forEach((alert) => store.addAlert(alert));
  });

  it("should provide access to all alerts", () => {
    const { result } = renderHook(() => useDealAlerts());

    expect(result.current.alerts).toHaveLength(2);
    expect(result.current.alerts.map((a) => a.id)).toContain(sampleAlerts[0].id);
    expect(result.current.alerts.map((a) => a.id)).toContain(sampleAlerts[1].id);
  });

  it("should provide access to active alerts", () => {
    const { result } = renderHook(() => useDealAlerts());

    expect(result.current.activeAlerts).toHaveLength(1);
    expect(result.current.activeAlerts[0].id).toBe(sampleAlerts[0].id);
  });

  it("should group alerts by type", () => {
    const { result } = renderHook(() => useDealAlerts());

    expect(Object.keys(result.current.alertsByType)).toHaveLength(2);
    expect(result.current.alertsByType["flight"]).toHaveLength(1);
    expect(result.current.alertsByType["accommodation"]).toHaveLength(1);
  });

  it("should toggle alert active state", () => {
    const { result } = renderHook(() => useDealAlerts());

    act(() => {
      result.current.toggleAlertActive(sampleAlerts[0].id);
    });

    expect(
      result.current.alerts.find((a) => a.id === sampleAlerts[0].id)?.isActive
    ).toBe(false);
    expect(result.current.activeAlerts).toHaveLength(0);
  });
});

describe("useFeaturedDeals Hook", () => {
  beforeEach(() => {
    // Reset store before each test
    const store = useDealsStore.getState();
    store.reset();

    // Add sample deals
    sampleDeals.forEach((deal) => store.addDeal(deal));

    // Add featured deal
    store.addToFeaturedDeals(sampleDeals[0].id);
  });

  it("should provide access to featured deals", () => {
    const { result } = renderHook(() => useFeaturedDeals());

    expect(result.current.featuredDeals).toHaveLength(1);
    expect(result.current.featuredDeals[0].id).toBe(sampleDeals[0].id);
  });

  it("should provide sorted featured deals", () => {
    const { result } = renderHook(() => useFeaturedDeals());

    expect(result.current.sortedByDiscount).toHaveLength(1);
    expect(result.current.sortedByDiscount[0].id).toBe(sampleDeals[0].id);
  });

  it("should provide top deals", () => {
    const { result } = renderHook(() => useFeaturedDeals());

    expect(result.current.topDeals).toHaveLength(1);
    expect(result.current.topDeals[0].id).toBe(sampleDeals[0].id);
  });

  it("should toggle featured status", () => {
    const { result } = renderHook(() => useFeaturedDeals());

    // Remove from featured
    act(() => {
      result.current.toggleFeatured(sampleDeals[0].id);
    });

    expect(result.current.featuredDeals).toHaveLength(0);
    expect(result.current.isDealFeatured(sampleDeals[0].id)).toBe(false);

    // Add back to featured
    act(() => {
      result.current.toggleFeatured(sampleDeals[0].id);
    });

    expect(result.current.featuredDeals).toHaveLength(1);
    expect(result.current.isDealFeatured(sampleDeals[0].id)).toBe(true);
  });
});

describe("useSavedDeals Hook", () => {
  beforeEach(() => {
    // Reset store before each test
    const store = useDealsStore.getState();
    store.reset();

    // Add sample deals
    sampleDeals.forEach((deal) => store.addDeal(deal));

    // Add saved deals
    store.addToSavedDeals(sampleDeals[0].id);
    store.addToSavedDeals(sampleDeals[1].id);
  });

  it("should provide access to saved deals", () => {
    const { result } = renderHook(() => useSavedDeals());

    expect(result.current.savedDeals).toHaveLength(2);
    expect(result.current.savedDeals.map((d) => d.id)).toContain(sampleDeals[0].id);
    expect(result.current.savedDeals.map((d) => d.id)).toContain(sampleDeals[1].id);
  });

  it("should provide sorted saved deals", () => {
    const { result } = renderHook(() => useSavedDeals());

    // Deals are sorted by expiry date, so the closer date should be first
    expect(result.current.sortedByExpiry).toHaveLength(2);
    expect(result.current.sortedByExpiry[0].id).toBe(sampleDeals[0].id); // Expires on June 1
    expect(result.current.sortedByExpiry[1].id).toBe(sampleDeals[1].id); // Expires on June 15
  });

  it("should toggle saved status", () => {
    const { result } = renderHook(() => useSavedDeals());

    // Remove from saved
    act(() => {
      result.current.toggleSaved(sampleDeals[0].id);
    });

    expect(result.current.savedDeals).toHaveLength(1);
    expect(result.current.isDealSaved(sampleDeals[0].id)).toBe(false);

    // Add back to saved
    act(() => {
      result.current.toggleSaved(sampleDeals[0].id);
    });

    expect(result.current.savedDeals).toHaveLength(2);
    expect(result.current.isDealSaved(sampleDeals[0].id)).toBe(true);
  });
});
