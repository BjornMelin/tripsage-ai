import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { DealType } from "@/types/deals";
import { useDealsStore } from "../deals-store";

// Mock current timestamp for consistent testing
const mockTimestamp = "2025-05-20T12:00:00.000Z";
vi.spyOn(Date.prototype, "toISOString").mockReturnValue(mockTimestamp);

// Sample deal data
const sampleDeal = {
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
};

// Sample alert data
const sampleAlert = {
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
};

describe("Deals Store", () => {
  beforeEach(() => {
    // Reset store before each test
    act(() => {
      useDealsStore.getState().reset();
    });
  });

  describe.skip("Deal Management", () => {
    it("should add a deal", () => {
      const { result } = renderHook(() => useDealsStore());

      let addResult: boolean;
      act(() => {
        addResult = result.current.addDeal(sampleDeal);
      });

      expect(addResult!).toBe(true);
      expect(result.current.deals[sampleDeal.id]).toEqual({
        ...sampleDeal,
        updatedAt: mockTimestamp,
      });
    });

    it("should reject an invalid deal", () => {
      const store = useDealsStore.getState();
      const invalidDeal = {
        id: "invalid1",
        // Missing required fields
      };

      const result = store.addDeal(invalidDeal);
      expect(result).toBe(false);
      expect(store.deals[invalidDeal.id as string]).toBeUndefined();
    });

    it("should update a deal", () => {
      const store = useDealsStore.getState();
      store.addDeal(sampleDeal);

      const updates = {
        price: 249.99,
        discountPercentage: 58,
      };

      const result = store.updateDeal(sampleDeal.id, updates);
      expect(result).toBe(true);
      expect(store.deals[sampleDeal.id].price).toBe(updates.price);
      expect(store.deals[sampleDeal.id].discountPercentage).toBe(
        updates.discountPercentage
      );
      expect(store.deals[sampleDeal.id].updatedAt).toBe(mockTimestamp);
    });

    it("should remove a deal", () => {
      const store = useDealsStore.getState();
      store.addDeal(sampleDeal);

      // Add to collections
      store.addToFeaturedDeals(sampleDeal.id);
      store.addToSavedDeals(sampleDeal.id);
      store.addToRecentlyViewed(sampleDeal.id);

      // Now remove
      store.removeDeal(sampleDeal.id);

      expect(store.deals[sampleDeal.id]).toBeUndefined();
      expect(store.featuredDeals).not.toContain(sampleDeal.id);
      expect(store.savedDeals).not.toContain(sampleDeal.id);
      expect(store.recentlyViewedDeals).not.toContain(sampleDeal.id);
    });
  });

  describe.skip("Featured Deals", () => {
    it("should add a deal to featured deals", () => {
      const store = useDealsStore.getState();
      store.addDeal(sampleDeal);
      store.addToFeaturedDeals(sampleDeal.id);

      expect(store.featuredDeals).toContain(sampleDeal.id);
    });

    it("should not add a non-existent deal to featured deals", () => {
      const store = useDealsStore.getState();
      store.addToFeaturedDeals("nonexistent");

      expect(store.featuredDeals).not.toContain("nonexistent");
    });

    it("should remove a deal from featured deals", () => {
      const store = useDealsStore.getState();
      store.addDeal(sampleDeal);
      store.addToFeaturedDeals(sampleDeal.id);
      store.removeFromFeaturedDeals(sampleDeal.id);

      expect(store.featuredDeals).not.toContain(sampleDeal.id);
    });

    it("should get featured deals", () => {
      const store = useDealsStore.getState();
      store.addDeal(sampleDeal);
      store.addToFeaturedDeals(sampleDeal.id);

      const featuredDeals = store.getFeaturedDeals();
      expect(featuredDeals).toHaveLength(1);
      expect(featuredDeals[0]).toEqual(
        expect.objectContaining({
          id: sampleDeal.id,
        })
      );
    });
  });

  describe.skip("Deal Alerts", () => {
    it("should add an alert", () => {
      const store = useDealsStore.getState();
      const result = store.addAlert(sampleAlert);

      expect(result).toBe(true);
      expect(store.alerts).toHaveLength(1);
      expect(store.alerts[0]).toEqual(
        expect.objectContaining({
          id: sampleAlert.id,
          updatedAt: mockTimestamp,
        })
      );
    });

    it("should reject an invalid alert", () => {
      const store = useDealsStore.getState();
      const invalidAlert = {
        id: "invalid1",
        // Missing required fields
      };

      const result = store.addAlert(invalidAlert);
      expect(result).toBe(false);
      expect(store.alerts).toHaveLength(0);
    });

    it("should update an alert", () => {
      const store = useDealsStore.getState();
      store.addAlert(sampleAlert);

      const updates = {
        minDiscount: 40,
        maxPrice: 350,
      };

      const result = store.updateAlert(sampleAlert.id, updates);
      expect(result).toBe(true);
      expect(store.alerts[0].minDiscount).toBe(updates.minDiscount);
      expect(store.alerts[0].maxPrice).toBe(updates.maxPrice);
      expect(store.alerts[0].updatedAt).toBe(mockTimestamp);
    });

    it("should toggle alert active state", () => {
      const store = useDealsStore.getState();
      store.addAlert(sampleAlert);

      const initialIsActive = store.alerts[0].isActive;
      store.toggleAlertActive(sampleAlert.id);

      expect(store.alerts[0].isActive).toBe(!initialIsActive);
      expect(store.alerts[0].updatedAt).toBe(mockTimestamp);
    });

    it("should remove an alert", () => {
      const store = useDealsStore.getState();
      store.addAlert(sampleAlert);
      store.removeAlert(sampleAlert.id);

      expect(store.alerts).toHaveLength(0);
    });
  });

  describe.skip("Saved Deals", () => {
    it("should add a deal to saved deals", () => {
      const store = useDealsStore.getState();
      store.addDeal(sampleDeal);
      store.addToSavedDeals(sampleDeal.id);

      expect(store.savedDeals).toContain(sampleDeal.id);
    });

    it("should not add a non-existent deal to saved deals", () => {
      const store = useDealsStore.getState();
      store.addToSavedDeals("nonexistent");

      expect(store.savedDeals).not.toContain("nonexistent");
    });

    it("should remove a deal from saved deals", () => {
      const store = useDealsStore.getState();
      store.addDeal(sampleDeal);
      store.addToSavedDeals(sampleDeal.id);
      store.removeFromSavedDeals(sampleDeal.id);

      expect(store.savedDeals).not.toContain(sampleDeal.id);
    });

    it("should get saved deals", () => {
      const store = useDealsStore.getState();
      store.addDeal(sampleDeal);
      store.addToSavedDeals(sampleDeal.id);

      const savedDeals = store.getSavedDeals();
      expect(savedDeals).toHaveLength(1);
      expect(savedDeals[0]).toEqual(
        expect.objectContaining({
          id: sampleDeal.id,
        })
      );
    });
  });

  describe.skip("Recently Viewed Deals", () => {
    it("should add a deal to recently viewed deals", () => {
      const store = useDealsStore.getState();
      store.addDeal(sampleDeal);
      store.addToRecentlyViewed(sampleDeal.id);

      expect(store.recentlyViewedDeals).toContain(sampleDeal.id);
    });

    it("should not add a non-existent deal to recently viewed deals", () => {
      const store = useDealsStore.getState();
      store.addToRecentlyViewed("nonexistent");

      expect(store.recentlyViewedDeals).not.toContain("nonexistent");
    });

    it("should clear recently viewed deals", () => {
      const store = useDealsStore.getState();
      store.addDeal(sampleDeal);
      store.addToRecentlyViewed(sampleDeal.id);
      store.clearRecentlyViewed();

      expect(store.recentlyViewedDeals).toHaveLength(0);
    });

    it("should get recently viewed deals", () => {
      const store = useDealsStore.getState();
      store.addDeal(sampleDeal);
      store.addToRecentlyViewed(sampleDeal.id);

      const recentlyViewedDeals = store.getRecentlyViewedDeals();
      expect(recentlyViewedDeals).toHaveLength(1);
      expect(recentlyViewedDeals[0]).toEqual(
        expect.objectContaining({
          id: sampleDeal.id,
        })
      );
    });

    it("should limit recently viewed deals to 20 items", () => {
      const store = useDealsStore.getState();

      // Add 25 deals
      for (let i = 0; i < 25; i++) {
        const deal = {
          ...sampleDeal,
          id: `deal${i}`,
          title: `Deal ${i}`,
        };
        store.addDeal(deal);
        store.addToRecentlyViewed(deal.id);
      }

      expect(store.recentlyViewedDeals).toHaveLength(20);
      expect(store.recentlyViewedDeals[0]).toBe("deal24"); // Most recent should be first
    });
  });

  describe("Filtering", () => {
    const flightDeal = {
      ...sampleDeal,
      id: "flight1",
      type: "flight" as DealType,
      destination: "Paris",
      origin: "New York",
    };

    const accommodationDeal = {
      ...sampleDeal,
      id: "accommodation1",
      type: "accommodation" as DealType,
      destination: "Rome",
      price: 150,
      originalPrice: 300,
      discountPercentage: 50,
    };

    const packageDeal = {
      ...sampleDeal,
      id: "package1",
      type: "package" as DealType,
      destination: "Barcelona",
      price: 899,
      originalPrice: 1499,
      discountPercentage: 40,
    };

    beforeEach(() => {
      const store = useDealsStore.getState();
      store.addDeal(flightDeal);
      store.addDeal(accommodationDeal);
      store.addDeal(packageDeal);
    });

    it("should filter deals by type", () => {
      const store = useDealsStore.getState();

      store.setFilters({
        types: ["flight"],
      });

      const filteredDeals = store.getFilteredDeals();
      expect(filteredDeals).toHaveLength(1);
      expect(filteredDeals[0].id).toBe(flightDeal.id);
    });

    it("should filter deals by destination", () => {
      const store = useDealsStore.getState();

      store.setFilters({
        destinations: ["Rome"],
      });

      const filteredDeals = store.getFilteredDeals();
      expect(filteredDeals).toHaveLength(1);
      expect(filteredDeals[0].id).toBe(accommodationDeal.id);
    });

    it("should filter deals by price", () => {
      const store = useDealsStore.getState();

      store.setFilters({
        maxPrice: 200,
      });

      const filteredDeals = store.getFilteredDeals();
      expect(filteredDeals).toHaveLength(1);
      expect(filteredDeals[0].id).toBe(accommodationDeal.id);
    });

    it("should filter deals by discount", () => {
      const store = useDealsStore.getState();

      store.setFilters({
        minDiscount: 45,
      });

      const filteredDeals = store.getFilteredDeals();
      expect(filteredDeals).toHaveLength(2);
      expect(filteredDeals.map((d) => d.id)).toContain(flightDeal.id);
      expect(filteredDeals.map((d) => d.id)).toContain(accommodationDeal.id);
    });

    it("should clear filters", () => {
      const store = useDealsStore.getState();

      store.setFilters({
        types: ["flight"],
      });

      store.clearFilters();

      const filteredDeals = store.getFilteredDeals();
      expect(filteredDeals).toHaveLength(3);
    });
  });

  describe("Stats", () => {
    const deals = [
      {
        ...sampleDeal,
        id: "flight1",
        type: "flight" as DealType,
        destination: "Paris",
        price: 299.99,
        originalPrice: 599.99,
        discountPercentage: 50,
      },
      {
        ...sampleDeal,
        id: "accommodation1",
        type: "accommodation" as DealType,
        destination: "Rome",
        price: 150,
        originalPrice: 300,
        discountPercentage: 50,
      },
      {
        ...sampleDeal,
        id: "package1",
        type: "package" as DealType,
        destination: "Paris",
        price: 899,
        originalPrice: 1499,
        discountPercentage: 40,
      },
    ];

    beforeEach(() => {
      const store = useDealsStore.getState();
      for (const deal of deals) {
        store.addDeal(deal);
      }
    });

    it("should calculate deal stats", () => {
      const store = useDealsStore.getState();
      const stats = store.getDealsStats();

      expect(stats.totalCount).toBe(3);
      expect(stats.byType).toEqual({
        flight: 1,
        accommodation: 1,
        package: 1,
      });
      expect(stats.byDestination).toEqual({
        Paris: 2,
        Rome: 1,
      });
      expect(stats.avgDiscount).toBeCloseTo(46.67, 1); // Average of 50, 50, 40
      expect(stats.avgSavings).toBeCloseTo(350, 0); // Average of 300, 150, 600
    });
  });

  describe.skip("Store Persistence", () => {
    it("should initialize the store", () => {
      const store = useDealsStore.getState();
      expect(store.isInitialized).toBe(false);

      store.initialize();
      expect(store.isInitialized).toBe(true);
    });

    it("should reset the store", () => {
      const store = useDealsStore.getState();

      // Setup some state
      store.addDeal(sampleDeal);
      store.addToFeaturedDeals(sampleDeal.id);
      store.addToSavedDeals(sampleDeal.id);
      store.addToRecentlyViewed(sampleDeal.id);
      store.addAlert(sampleAlert);
      store.setFilters({ types: ["flight"] });
      store.initialize();

      // Reset
      store.reset();

      // Verify reset
      expect(store.deals).toEqual({});
      expect(store.featuredDeals).toEqual([]);
      expect(store.savedDeals).toEqual([]);
      expect(store.recentlyViewedDeals).toEqual([]);
      expect(store.alerts).toEqual([]);
      expect(store.filters).toBeUndefined();
      expect(store.isInitialized).toBe(false);
    });
  });
});
