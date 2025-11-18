/** @vitest-environment jsdom */

import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { DealType } from "@/lib/schemas/deals";
import {
  createDealAlertFixture,
  createDealFixture,
  createInvalidDealAlertFixture,
  createInvalidDealFixture,
} from "@/test/fixtures/deals";
import { useDealsStore } from "../deals-store";

// Mock current timestamp for consistent testing
/** Mock timestamp for consistent date-based testing */
const MOCK_TIMESTAMP = "2025-05-20T12:00:00.000Z";
vi.spyOn(Date.prototype, "toISOString").mockReturnValue(MOCK_TIMESTAMP);

// Use Zod-validated fixtures
const SAMPLE_DEAL = createDealFixture({
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
  type: "flight",
  updatedAt: "2025-05-01T00:00:00.000Z",
  url: "https://example.com/deal1",
  verified: true,
});

const SAMPLE_ALERT = createDealAlertFixture({
  createdAt: "2025-05-01T00:00:00.000Z",
  dealType: "flight",
  destination: "Paris",
  id: "alert1",
  isActive: true,
  maxPrice: 400,
  minDiscount: 30,
  notificationType: "email",
  origin: "New York",
  updatedAt: "2025-05-01T00:00:00.000Z",
  userId: "user1",
});

describe("Deals Store", () => {
  beforeEach(() => {
    // Reset store before each test
    act(() => {
      useDealsStore.getState().reset();
    });
  });

  describe("Deal Management", () => {
    it("should add a deal", () => {
      const { result } = renderHook(() => useDealsStore());

      let addResult: boolean;
      act(() => {
        addResult = result.current.addDeal(SAMPLE_DEAL);
      });

      // biome-ignore lint/style/noNonNullAssertion: Test assertion after assignment
      expect(addResult!).toBe(true);
      expect(result.current.deals[SAMPLE_DEAL.id]).toEqual(
        expect.objectContaining({
          ...SAMPLE_DEAL,
          updatedAt: expect.any(String),
        })
      );
    });

    it("should reject an invalid deal", () => {
      const store = useDealsStore.getState();
      const invalidDeal = createInvalidDealFixture();

      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {
        // Suppress console.error during test
      });

      const result = store.addDeal(invalidDeal);
      expect(result).toBe(false);
      expect(store.deals.invalid1).toBeUndefined();
      expect(consoleSpy).toHaveBeenCalledWith(
        "Invalid deal data:",
        expect.any(Object) // ZodError
      );

      consoleSpy.mockRestore();
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
      const updated = useDealsStore.getState();
      expect(updated.deals[SAMPLE_DEAL.id].price).toBe(updates.price);
      expect(updated.deals[SAMPLE_DEAL.id].discountPercentage).toBe(
        updates.discountPercentage
      );
      expect(typeof updated.deals[SAMPLE_DEAL.id].updatedAt).toBe("string");
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

  describe("Featured Deals", () => {
    it("should add a deal to featured deals", () => {
      const store = useDealsStore.getState();
      store.addDeal(SAMPLE_DEAL);
      store.addToFeaturedDeals(SAMPLE_DEAL.id);
      expect(useDealsStore.getState().featuredDeals).toContain(SAMPLE_DEAL.id);
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

  describe("Deal Alerts", () => {
    it("should add an alert", () => {
      const store = useDealsStore.getState();
      const result = store.addAlert(SAMPLE_ALERT);

      expect(result).toBe(true);
      const afterAddAlert = useDealsStore.getState();
      expect(afterAddAlert.alerts).toHaveLength(1);
      expect(afterAddAlert.alerts[0]).toEqual(
        expect.objectContaining({
          id: SAMPLE_ALERT.id,
          updatedAt: expect.any(String),
        })
      );
    });

    it("should reject an invalid alert", () => {
      const store = useDealsStore.getState();
      const invalidAlert = createInvalidDealAlertFixture();

      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {
        // Suppress console.error during test
      });

      const result = store.addAlert(invalidAlert);
      expect(result).toBe(false);
      expect(store.alerts).toHaveLength(0);
      expect(consoleSpy).toHaveBeenCalledWith(
        "Invalid alert data:",
        expect.any(Object) // ZodError
      );

      consoleSpy.mockRestore();
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
      const alertState = useDealsStore.getState();
      expect(alertState.alerts[0].minDiscount).toBe(updates.minDiscount);
      expect(alertState.alerts[0].maxPrice).toBe(updates.maxPrice);
      expect(typeof alertState.alerts[0].updatedAt).toBe("string");
    });

    it("should toggle alert active state", () => {
      const store = useDealsStore.getState();
      store.addAlert(SAMPLE_ALERT);

      const initialIsActive = useDealsStore.getState().alerts[0].isActive;
      store.toggleAlertActive(SAMPLE_ALERT.id);
      const toggled = useDealsStore.getState();
      expect(toggled.alerts[0].isActive).toBe(!initialIsActive);
      expect(typeof toggled.alerts[0].updatedAt).toBe("string");
    });

    it("should remove an alert", () => {
      const store = useDealsStore.getState();
      store.addAlert(SAMPLE_ALERT);
      store.removeAlert(SAMPLE_ALERT.id);

      expect(store.alerts).toHaveLength(0);
    });
  });

  describe("Saved Deals", () => {
    it("should add a deal to saved deals", () => {
      const store = useDealsStore.getState();
      store.addDeal(SAMPLE_DEAL);
      store.addToSavedDeals(SAMPLE_DEAL.id);
      expect(useDealsStore.getState().savedDeals).toContain(SAMPLE_DEAL.id);
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

  describe("Recently Viewed Deals", () => {
    it("should add a deal to recently viewed deals", () => {
      const store = useDealsStore.getState();
      store.addDeal(SAMPLE_DEAL);
      store.addToRecentlyViewed(SAMPLE_DEAL.id);
      expect(useDealsStore.getState().recentlyViewedDeals).toContain(SAMPLE_DEAL.id);
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

      const recentState = useDealsStore.getState();
      expect(recentState.recentlyViewedDeals).toHaveLength(20);
      expect(recentState.recentlyViewedDeals[0]).toBe("deal24"); // Most recent should be first
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

  describe("Store Persistence", () => {
    it("should initialize the store", () => {
      const store = useDealsStore.getState();
      expect(store.isInitialized).toBe(false);

      store.initialize();
      expect(useDealsStore.getState().isInitialized).toBe(true);
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
