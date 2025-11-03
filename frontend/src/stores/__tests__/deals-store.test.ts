/**
 * @fileoverview Unit tests for the deals store functionality.
 * Tests deal and alert management, statistics calculation, and store state operations.
 */
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { DealType } from "@/types/deals";
import { useDealsStore } from "../deals-store";

// Mock current timestamp for consistent testing
/** Mock timestamp for consistent date-based testing */
const MOCK_TIMESTAMP = "2025-05-20T12:00:00.000Z";
vi.spyOn(Date.prototype, "toISOString").mockReturnValue(MOCK_TIMESTAMP);

// Sample deal data
/** Sample flight deal for testing purposes */
const SAMPLE_DEAL = {
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
};

// Sample alert data
/** Sample deal alert for testing purposes */
const SAMPLE_ALERT = {
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
        addResult = result.current.addDeal(SAMPLE_DEAL);
      });

      expect(addResult!).toBe(true);
      expect(result.current.deals[SAMPLE_DEAL.id]).toEqual({
        ...SAMPLE_DEAL,
        updatedAt: MOCK_TIMESTAMP,
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
      store.addDeal(SAMPLE_DEAL);

      const updates = {
        discountPercentage: 58,
        price: 249.99,
      };

      const result = store.updateDeal(SAMPLE_DEAL.id, updates);
      expect(result).toBe(true);
      expect(store.deals[SAMPLE_DEAL.id].price).toBe(updates.price);
      expect(store.deals[SAMPLE_DEAL.id].discountPercentage).toBe(
        updates.discountPercentage
      );
      expect(store.deals[SAMPLE_DEAL.id].updatedAt).toBe(MOCK_TIMESTAMP);
    });

    it("should remove a deal", () => {
      const store = useDealsStore.getState();
      store.addDeal(SAMPLE_DEAL);

      // Add to collections
      store.addToFeaturedDeals(SAMPLE_DEAL.id);
      store.addToSavedDeals(SAMPLE_DEAL.id);
      store.addToRecentlyViewed(SAMPLE_DEAL.id);

      // Now remove
      store.removeDeal(SAMPLE_DEAL.id);

      expect(store.deals[SAMPLE_DEAL.id]).toBeUndefined();
      expect(store.featuredDeals).not.toContain(SAMPLE_DEAL.id);
      expect(store.savedDeals).not.toContain(SAMPLE_DEAL.id);
      expect(store.recentlyViewedDeals).not.toContain(SAMPLE_DEAL.id);
    });
  });

  describe.skip("Featured Deals", () => {
    it("should add a deal to featured deals", () => {
      const store = useDealsStore.getState();
      store.addDeal(SAMPLE_DEAL);
      store.addToFeaturedDeals(SAMPLE_DEAL.id);

      expect(store.featuredDeals).toContain(SAMPLE_DEAL.id);
    });

    it("should not add a non-existent deal to featured deals", () => {
      const store = useDealsStore.getState();
      store.addToFeaturedDeals("nonexistent");

      expect(store.featuredDeals).not.toContain("nonexistent");
    });

    it("should remove a deal from featured deals", () => {
      const store = useDealsStore.getState();
      store.addDeal(SAMPLE_DEAL);
      store.addToFeaturedDeals(SAMPLE_DEAL.id);
      store.removeFromFeaturedDeals(SAMPLE_DEAL.id);

      expect(store.featuredDeals).not.toContain(SAMPLE_DEAL.id);
    });

    it("should get featured deals", () => {
      const store = useDealsStore.getState();
      store.addDeal(SAMPLE_DEAL);
      store.addToFeaturedDeals(SAMPLE_DEAL.id);

      const featuredDeals = store.getFeaturedDeals();
      expect(featuredDeals).toHaveLength(1);
      expect(featuredDeals[0]).toEqual(
        expect.objectContaining({
          id: SAMPLE_DEAL.id,
        })
      );
    });
  });

  describe.skip("Deal Alerts", () => {
    it("should add an alert", () => {
      const store = useDealsStore.getState();
      const result = store.addAlert(SAMPLE_ALERT);

      expect(result).toBe(true);
      expect(store.alerts).toHaveLength(1);
      expect(store.alerts[0]).toEqual(
        expect.objectContaining({
          id: SAMPLE_ALERT.id,
          updatedAt: MOCK_TIMESTAMP,
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
      store.addAlert(SAMPLE_ALERT);

      const updates = {
        maxPrice: 350,
        minDiscount: 40,
      };

      const result = store.updateAlert(SAMPLE_ALERT.id, updates);
      expect(result).toBe(true);
      expect(store.alerts[0].minDiscount).toBe(updates.minDiscount);
      expect(store.alerts[0].maxPrice).toBe(updates.maxPrice);
      expect(store.alerts[0].updatedAt).toBe(MOCK_TIMESTAMP);
    });

    it("should toggle alert active state", () => {
      const store = useDealsStore.getState();
      store.addAlert(SAMPLE_ALERT);

      const initialIsActive = store.alerts[0].isActive;
      store.toggleAlertActive(SAMPLE_ALERT.id);

      expect(store.alerts[0].isActive).toBe(!initialIsActive);
      expect(store.alerts[0].updatedAt).toBe(MOCK_TIMESTAMP);
    });

    it("should remove an alert", () => {
      const store = useDealsStore.getState();
      store.addAlert(SAMPLE_ALERT);
      store.removeAlert(SAMPLE_ALERT.id);

      expect(store.alerts).toHaveLength(0);
    });
  });

  describe.skip("Saved Deals", () => {
    it("should add a deal to saved deals", () => {
      const store = useDealsStore.getState();
      store.addDeal(SAMPLE_DEAL);
      store.addToSavedDeals(SAMPLE_DEAL.id);

      expect(store.savedDeals).toContain(SAMPLE_DEAL.id);
    });

    it("should not add a non-existent deal to saved deals", () => {
      const store = useDealsStore.getState();
      store.addToSavedDeals("nonexistent");

      expect(store.savedDeals).not.toContain("nonexistent");
    });

    it("should remove a deal from saved deals", () => {
      const store = useDealsStore.getState();
      store.addDeal(SAMPLE_DEAL);
      store.addToSavedDeals(SAMPLE_DEAL.id);
      store.removeFromSavedDeals(SAMPLE_DEAL.id);

      expect(store.savedDeals).not.toContain(SAMPLE_DEAL.id);
    });

    it("should get saved deals", () => {
      const store = useDealsStore.getState();
      store.addDeal(SAMPLE_DEAL);
      store.addToSavedDeals(SAMPLE_DEAL.id);

      const savedDeals = store.getSavedDeals();
      expect(savedDeals).toHaveLength(1);
      expect(savedDeals[0]).toEqual(
        expect.objectContaining({
          id: SAMPLE_DEAL.id,
        })
      );
    });
  });

  describe.skip("Recently Viewed Deals", () => {
    it("should add a deal to recently viewed deals", () => {
      const store = useDealsStore.getState();
      store.addDeal(SAMPLE_DEAL);
      store.addToRecentlyViewed(SAMPLE_DEAL.id);

      expect(store.recentlyViewedDeals).toContain(SAMPLE_DEAL.id);
    });

    it("should not add a non-existent deal to recently viewed deals", () => {
      const store = useDealsStore.getState();
      store.addToRecentlyViewed("nonexistent");

      expect(store.recentlyViewedDeals).not.toContain("nonexistent");
    });

    it("should clear recently viewed deals", () => {
      const store = useDealsStore.getState();
      store.addDeal(SAMPLE_DEAL);
      store.addToRecentlyViewed(SAMPLE_DEAL.id);
      store.clearRecentlyViewed();

      expect(store.recentlyViewedDeals).toHaveLength(0);
    });

    it("should get recently viewed deals", () => {
      const store = useDealsStore.getState();
      store.addDeal(SAMPLE_DEAL);
      store.addToRecentlyViewed(SAMPLE_DEAL.id);

      const recentlyViewedDeals = store.getRecentlyViewedDeals();
      expect(recentlyViewedDeals).toHaveLength(1);
      expect(recentlyViewedDeals[0]).toEqual(
        expect.objectContaining({
          id: SAMPLE_DEAL.id,
        })
      );
    });

    it("should limit recently viewed deals to 20 items", () => {
      const store = useDealsStore.getState();

      // Add 25 deals
      for (let i = 0; i < 25; i++) {
        const deal = {
          ...SAMPLE_DEAL,
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
      ...SAMPLE_DEAL,
      destination: "Paris",
      id: "flight1",
      origin: "New York",
      type: "flight" as DealType,
    };

    const accommodationDeal = {
      ...SAMPLE_DEAL,
      destination: "Rome",
      discountPercentage: 50,
      id: "accommodation1",
      originalPrice: 300,
      price: 150,
      type: "accommodation" as DealType,
    };

    const packageDeal = {
      ...SAMPLE_DEAL,
      destination: "Barcelona",
      discountPercentage: 40,
      id: "package1",
      originalPrice: 1499,
      price: 899,
      type: "package" as DealType,
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
        ...SAMPLE_DEAL,
        destination: "Paris",
        discountPercentage: 50,
        id: "flight1",
        originalPrice: 599.99,
        price: 299.99,
        type: "flight" as DealType,
      },
      {
        ...SAMPLE_DEAL,
        destination: "Rome",
        discountPercentage: 50,
        id: "accommodation1",
        originalPrice: 300,
        price: 150,
        type: "accommodation" as DealType,
      },
      {
        ...SAMPLE_DEAL,
        destination: "Paris",
        discountPercentage: 40,
        id: "package1",
        originalPrice: 1499,
        price: 899,
        type: "package" as DealType,
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
        accommodation: 1,
        activity: 0,
        error_fare: 0,
        flash_sale: 0,
        flight: 1,
        package: 1,
        promotion: 0,
        transportation: 0,
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
      store.addDeal(SAMPLE_DEAL);
      store.addToFeaturedDeals(SAMPLE_DEAL.id);
      store.addToSavedDeals(SAMPLE_DEAL.id);
      store.addToRecentlyViewed(SAMPLE_DEAL.id);
      store.addAlert(SAMPLE_ALERT);
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
