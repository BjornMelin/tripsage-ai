/** @vitest-environment jsdom */

import type { Activity } from "@schemas/search";
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  useComparisonItemsByType,
  useComparisonStore,
} from "@/features/search/store/comparison-store";

vi.unmock("zustand/middleware");

const activityStub: Activity = {
  date: "2026-01-01",
  description: "Guided museum visit",
  duration: 2,
  id: "activity-persisted",
  location: "Paris",
  name: "Museum Tour",
  price: 25,
  rating: 4.5,
  type: "Museum",
};

function persistedActivity(id: string) {
  return {
    addedAt: "2026-01-01T00:00:00.000Z",
    data: { ...activityStub, id },
    id,
    type: "activity" as const,
  };
}

describe("comparison-store persistence", () => {
  beforeEach(() => {
    useComparisonStore.getState().reset();
    useComparisonStore.persist.clearStorage();
  });

  afterEach(() => {
    useComparisonStore.getState().reset();
    useComparisonStore.persist.clearStorage();
  });

  it("hydrates initial computed state when storage is empty", async () => {
    await act(async () => {
      await useComparisonStore.persist.rehydrate();
    });

    const store = useComparisonStore.getState();
    expect(useComparisonStore.persist.hasHydrated()).toBe(true);
    expect(store.itemCount).toBe(0);
    expect(store.canAdd).toBe(true);
    expect(store.idsSet.size).toBe(0);
    expect(store.itemsByTypeMap.size).toBe(0);
  });

  it.each([
    { items: { invalid: true }, maxItems: 3 },
    { items: [null], maxItems: 3 },
    {
      items: [
        {
          addedAt: "2026-01-01T00:00:00.000Z",
          data: {},
          id: "activity-invalid",
          type: "activity",
        },
      ],
      maxItems: 3,
    },
    {
      items: [
        persistedActivity("activity-1"),
        persistedActivity("activity-2"),
        persistedActivity("activity-3"),
        persistedActivity("activity-4"),
      ],
      maxItems: 3,
    },
    {
      items: [
        persistedActivity("activity-duplicate"),
        persistedActivity("activity-duplicate"),
      ],
      maxItems: 3,
    },
    {
      items: [
        {
          ...persistedActivity("activity-wrapper"),
          data: { ...activityStub, id: "activity-data" },
        },
      ],
      maxItems: 3,
    },
  ])("falls back safely for malformed persisted state %#", async (state) => {
    localStorage.setItem("comparison-storage", JSON.stringify({ state, version: 0 }));

    await act(async () => {
      await useComparisonStore.persist.rehydrate();
    });

    const store = useComparisonStore.getState();
    expect(useComparisonStore.persist.hasHydrated()).toBe(true);
    expect(store.items).toEqual([]);
    expect(store.maxItems).toBe(3);
    expect(store.itemCount).toBe(0);
    expect(store.itemsByTypeMap.size).toBe(0);
  });

  it("retains valid legacy items without restoring the old comparison limit", async () => {
    localStorage.setItem(
      "comparison-storage",
      JSON.stringify({
        state: {
          items: [persistedActivity(activityStub.id)],
          maxItems: 999_999,
        },
        version: 0,
      })
    );

    await act(async () => {
      await useComparisonStore.persist.rehydrate();
    });

    const store = useComparisonStore.getState();
    expect(store.items).toHaveLength(1);
    expect(store.maxItems).toBe(3);
  });

  it("recomputes derived state when persisted items are rehydrated", async () => {
    localStorage.setItem(
      "comparison-storage",
      JSON.stringify({
        state: {
          items: [persistedActivity("activity-persisted")],
          maxItems: 3,
        },
        version: 0,
      })
    );

    await act(async () => {
      await useComparisonStore.persist.rehydrate();
    });

    const store = useComparisonStore.getState();
    expect(store.itemCount).toBe(1);
    expect(store.canAdd).toBe(true);
    expect(store.idsSet.has("activity-persisted")).toBe(true);
    expect(store.itemsByTypeMap.get("activity")).toEqual([
      expect.objectContaining({ id: "activity-persisted", type: "activity" }),
    ]);

    const { result } = renderHook(() => useComparisonItemsByType("activity"));
    expect(result.current).toEqual([
      expect.objectContaining({ id: "activity-persisted", type: "activity" }),
    ]);
  });
});
