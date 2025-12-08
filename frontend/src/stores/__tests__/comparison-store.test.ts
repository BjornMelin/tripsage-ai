/** @vitest-environment jsdom */

import type { Accommodation, Activity, FlightResult } from "@schemas/search";
import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import {
  useCanAddComparison,
  useComparisonItemCount,
  useComparisonItems,
  useComparisonStore,
  useHasComparisonItem,
} from "../comparison-store";

const flightStub = {} as FlightResult;
const accommodationStub = {} as Accommodation;
const activityStub = {} as Activity;

const addFlight = (id = "flight-1", data: FlightResult = flightStub) =>
  useComparisonStore.getState().addItem("flight", id, data);
const addAccommodation = (
  id = "accommodation-1",
  data: Accommodation = accommodationStub
) => useComparisonStore.getState().addItem("accommodation", id, data);
const addActivity = (id = "activity-1", data: Activity = activityStub) =>
  useComparisonStore.getState().addItem("activity", id, data);
describe("comparison-store", () => {
  afterEach(() => {
    // Clean up after each test
    useComparisonStore.getState().reset();
  });

  describe("initial state", () => {
    it("should have empty items array", () => {
      expect(useComparisonStore.getState().items).toEqual([]);
    });

    it("should have default maxItems of 3", () => {
      expect(useComparisonStore.getState().maxItems).toBe(3);
    });

    it("should have itemCount of 0", () => {
      expect(useComparisonStore.getState().itemCount).toBe(0);
    });

    it("should have canAdd as true", () => {
      expect(useComparisonStore.getState().canAdd).toBe(true);
    });

    it("should have empty itemsByTypeMap", () => {
      expect(useComparisonStore.getState().itemsByTypeMap.size).toBe(0);
    });
  });

  describe("addItem", () => {
    it("should add item successfully", () => {
      const result = addFlight("flight-1");

      expect(result).toBe(true);
      expect(useComparisonStore.getState().items).toHaveLength(1);
      expect(useComparisonStore.getState().items[0]).toMatchObject({
        data: flightStub,
        id: "flight-1",
        type: "flight",
      });
    });

    it("should add items up to maxItems", () => {
      addFlight("flight-1");
      addFlight("flight-2");
      addFlight("flight-3");

      expect(useComparisonStore.getState().items).toHaveLength(3);
      expect(useComparisonStore.getState().canAdd).toBe(false);
    });

    it("should reject item when at maxItems", () => {
      addFlight("flight-1");
      addFlight("flight-2");
      addFlight("flight-3");

      const result = addFlight("flight-4");

      expect(result).toBe(false);
      expect(useComparisonStore.getState().items).toHaveLength(3);
    });

    it("should reject duplicate items by id", () => {
      addFlight("flight-1");
      const result = addFlight("flight-1");

      expect(result).toBe(false);
      expect(useComparisonStore.getState().items).toHaveLength(1);
      expect(useComparisonStore.getState().items[0].data).toEqual(flightStub);
    });

    it("should set addedAt timestamp", () => {
      addFlight("flight-1");
      const item = useComparisonStore.getState().items[0];

      expect(item.addedAt).toBeDefined();
      expect(typeof item.addedAt).toBe("string");
      // Should be a valid ISO date
      expect(new Date(item.addedAt).toISOString()).toBe(item.addedAt);
    });

    it("should support different search types", () => {
      addFlight("flight-1");
      addAccommodation("accommodation-1");
      addActivity("activity-1");

      expect(useComparisonStore.getState().items).toHaveLength(3);
      expect(useComparisonStore.getState().getItemsByType("flight")).toHaveLength(1);
      expect(
        useComparisonStore.getState().getItemsByType("accommodation")
      ).toHaveLength(1);
      expect(useComparisonStore.getState().getItemsByType("activity")).toHaveLength(1);
    });
  });

  describe("removeItem", () => {
    it("should remove item by id", () => {
      addFlight("flight-1");
      addFlight("flight-2");

      useComparisonStore.getState().removeItem("flight-1");

      expect(useComparisonStore.getState().items).toHaveLength(1);
      expect(useComparisonStore.getState().items[0].id).toBe("flight-2");
    });

    it("should update computed state after removal", () => {
      addFlight("flight-1");
      addFlight("flight-2");
      addFlight("flight-3");

      expect(useComparisonStore.getState().canAdd).toBe(false);

      useComparisonStore.getState().removeItem("flight-1");

      expect(useComparisonStore.getState().canAdd).toBe(true);
      expect(useComparisonStore.getState().itemCount).toBe(2);
    });

    it("should handle removal of non-existent item", () => {
      addFlight("flight-1");

      useComparisonStore.getState().removeItem("non-existent");

      expect(useComparisonStore.getState().items).toHaveLength(1);
    });
  });

  describe("clearByType", () => {
    it("should clear all items of a specific type", () => {
      addFlight("flight-1");
      addFlight("flight-2");
      addAccommodation("accommodation-1");

      useComparisonStore.getState().clearByType("flight");

      expect(useComparisonStore.getState().items).toHaveLength(1);
      expect(useComparisonStore.getState().items[0].type).toBe("accommodation");
    });

    it("should not affect items of other types", () => {
      addFlight("flight-1");
      addAccommodation("accommodation-1");

      useComparisonStore.getState().clearByType("activity");

      expect(useComparisonStore.getState().items).toHaveLength(2);
    });

    it("should update computed itemsByTypeMap", () => {
      addFlight("flight-1");
      addFlight("flight-2");

      useComparisonStore.getState().clearByType("flight");

      expect(useComparisonStore.getState().getItemsByType("flight")).toHaveLength(0);
    });
  });

  describe("clearAll", () => {
    it("should remove all items", () => {
      addFlight("flight-1");
      addAccommodation("accommodation-1");
      addActivity("activity-1");

      useComparisonStore.getState().clearAll();

      expect(useComparisonStore.getState().items).toHaveLength(0);
      expect(useComparisonStore.getState().itemCount).toBe(0);
      expect(useComparisonStore.getState().canAdd).toBe(true);
      expect(useComparisonStore.getState().itemsByTypeMap.size).toBe(0);
      expect(useComparisonStore.getState().idsSet.size).toBe(0);
    });
  });

  describe("hasItem", () => {
    it("should return true for existing item", () => {
      addFlight("flight-1");

      expect(useComparisonStore.getState().hasItem("flight-1")).toBe(true);
    });

    it("should return false for non-existing item", () => {
      addFlight("flight-1");

      expect(useComparisonStore.getState().hasItem("flight-2")).toBe(false);
    });
  });

  describe("getItemsByType", () => {
    it("should return items filtered by type", () => {
      addFlight("flight-1");
      addFlight("flight-2");
      addAccommodation("accommodation-1");

      const flights = useComparisonStore.getState().getItemsByType("flight");

      expect(flights).toHaveLength(2);
      expect(flights.every((item) => item.type === "flight")).toBe(true);
    });

    it("should return empty array for type with no items", () => {
      addFlight("flight-1");

      const activities = useComparisonStore.getState().getItemsByType("activity");

      expect(activities).toHaveLength(0);
    });
  });

  describe("reset", () => {
    it("should reset to initial state", () => {
      addFlight("flight-1");
      addFlight("flight-2");

      useComparisonStore.getState().reset();

      expect(useComparisonStore.getState().items).toEqual([]);
      expect(useComparisonStore.getState().maxItems).toBe(3);
      expect(useComparisonStore.getState().itemCount).toBe(0);
      expect(useComparisonStore.getState().canAdd).toBe(true);
    });
  });

  describe("computed state", () => {
    it("should update itemCount on add/remove", () => {
      expect(useComparisonStore.getState().itemCount).toBe(0);

      addFlight("flight-1");
      expect(useComparisonStore.getState().itemCount).toBe(1);

      addFlight("flight-2");
      expect(useComparisonStore.getState().itemCount).toBe(2);

      useComparisonStore.getState().removeItem("flight-1");
      expect(useComparisonStore.getState().itemCount).toBe(1);
    });

    it("should update canAdd correctly", () => {
      expect(useComparisonStore.getState().canAdd).toBe(true);

      addFlight("flight-1");
      addFlight("flight-2");
      expect(useComparisonStore.getState().canAdd).toBe(true);

      addFlight("flight-3");
      expect(useComparisonStore.getState().canAdd).toBe(false);

      useComparisonStore.getState().removeItem("flight-3");
      expect(useComparisonStore.getState().canAdd).toBe(true);
    });

    it("should update itemsByTypeMap correctly", () => {
      addFlight("flight-1");
      addAccommodation("accommodation-1");
      addFlight("flight-2");

      const store = useComparisonStore.getState();

      expect(store.getItemsByType("flight")).toHaveLength(2);
      expect(store.getItemsByType("accommodation")).toHaveLength(1);
      expect(store.getItemsByType("activity")).toHaveLength(0);
    });
  });

  describe("selector hooks", () => {
    it("useComparisonItems should return items", () => {
      addFlight("flight-1");

      const { result } = renderHook(() => useComparisonItems());

      expect(result.current).toHaveLength(1);

      act(() => useComparisonStore.getState().removeItem("flight-1"));
      expect(result.current).toHaveLength(0);
    });

    it("useComparisonItemCount should return count", () => {
      const { result, rerender } = renderHook(() => useComparisonItemCount());
      expect(result.current).toBe(0);

      act(() => {
        addFlight("flight-1");
        addFlight("flight-2");
      });
      rerender();
      expect(result.current).toBe(2);
    });

    it("useCanAddComparison should return canAdd state", () => {
      const { result, rerender } = renderHook(() => useCanAddComparison());

      expect(result.current).toBe(true);

      act(() => {
        addFlight("flight-1");
        addFlight("flight-2");
        addFlight("flight-3");
      });

      rerender();
      expect(result.current).toBe(false);
    });

    it("useHasComparisonItem should check for item", () => {
      addFlight("flight-1");

      const { result: hasResult } = renderHook(() => useHasComparisonItem("flight-1"));
      const { result: noResult } = renderHook(() => useHasComparisonItem("flight-2"));

      expect(hasResult.current).toBe(true);
      expect(noResult.current).toBe(false);

      act(() => useComparisonStore.getState().removeItem("flight-1"));
      expect(hasResult.current).toBe(false);
    });
  });

  describe("internal state consistency", () => {
    it("should keep itemsByTypeMap and idsSet consistent after addItem", () => {
      addFlight("flight-persist", flightStub);

      const store = useComparisonStore.getState();
      expect(store.getItemsByType("flight")).toHaveLength(1);
      expect(store.itemsByTypeMap.get("flight")?.length).toBe(1);
      expect(store.idsSet.has("flight-persist")).toBe(true);
    });
  });
});
