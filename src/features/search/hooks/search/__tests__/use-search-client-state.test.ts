/** @vitest-environment jsdom */

import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import {
  isAbortError,
  toggleStringSetValue,
  useAbortableSearchTask,
  usePersistentStringSet,
} from "../use-search-client-state";

describe("search client state helpers", () => {
  afterEach(() => {
    window.localStorage.clear();
  });

  it("detects abort errors", () => {
    const abortError = new Error("cancelled");
    abortError.name = "AbortError";

    expect(isAbortError(abortError)).toBe(true);
    expect(isAbortError(new Error("other"))).toBe(false);
    expect(isAbortError("AbortError")).toBe(false);
  });

  it("aborts the previous search task and cleans up the active task on unmount", () => {
    const { result, unmount } = renderHook(() => useAbortableSearchTask());

    const firstController = result.current.startSearchController();
    expect(firstController.signal.aborted).toBe(false);

    const secondController = result.current.startSearchController();
    expect(firstController.signal.aborted).toBe(true);
    expect(secondController.signal.aborted).toBe(false);

    result.current.clearSearchController(firstController);
    unmount();

    expect(secondController.signal.aborted).toBe(true);
  });

  it("loads and persists string sets", async () => {
    window.localStorage.setItem("search:test", JSON.stringify(["hotel-1"]));

    const { result } = renderHook(() => usePersistentStringSet("search:test"));

    await waitFor(() => expect(result.current[0].has("hotel-1")).toBe(true));

    act(() => {
      result.current[1](new Set(["hotel-2", "hotel-3"]));
    });

    expect(result.current[0]).toEqual(new Set(["hotel-2", "hotel-3"]));
    expect(window.localStorage.getItem("search:test")).toBe(
      JSON.stringify(["hotel-2", "hotel-3"])
    );
  });

  it("persists functional string-set updates from the latest value", async () => {
    const { result } = renderHook(() => usePersistentStringSet("search:test"));

    act(() => {
      result.current[1]((currentValues) => {
        const toggled = toggleStringSetValue(currentValues, "hotel-1");
        return toggled.nextValues;
      });
      result.current[1]((currentValues) => {
        const toggled = toggleStringSetValue(currentValues, "hotel-2");
        return toggled.nextValues;
      });
    });

    await waitFor(() =>
      expect(result.current[0]).toEqual(new Set(["hotel-1", "hotel-2"]))
    );
    expect(window.localStorage.getItem("search:test")).toBe(
      JSON.stringify(["hotel-1", "hotel-2"])
    );
  });

  it("ignores invalid persisted string-set payloads", async () => {
    window.localStorage.setItem("search:test", JSON.stringify(["hotel-1", 42]));

    const { result } = renderHook(() => usePersistentStringSet("search:test"));

    await waitFor(() => expect(result.current[0].size).toBe(0));
  });

  it("toggles set values without mutating the source set", () => {
    const source = new Set(["hotel-1"]);

    const removed = toggleStringSetValue(source, "hotel-1");
    const added = toggleStringSetValue(source, "hotel-2");

    expect(source).toEqual(new Set(["hotel-1"]));
    expect(removed).toEqual({ nextValues: new Set(), wasPresent: true });
    expect(added).toEqual({
      nextValues: new Set(["hotel-1", "hotel-2"]),
      wasPresent: false,
    });
  });
});
