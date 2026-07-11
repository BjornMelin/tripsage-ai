/** @vitest-environment jsdom */

import type { Activity } from "@schemas/search";
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  useComparisonItemsByType,
  useComparisonStore,
} from "@/features/search/store/comparison-store";

vi.unmock("zustand/middleware");

const activityStub = {} as Activity;

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

  it("recomputes derived state when persisted items are rehydrated", async () => {
    localStorage.setItem(
      "comparison-storage",
      JSON.stringify({
        state: {
          items: [
            {
              addedAt: "2026-01-01T00:00:00.000Z",
              data: activityStub,
              id: "activity-persisted",
              type: "activity",
            },
          ],
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
