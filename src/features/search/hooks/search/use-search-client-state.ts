/**
 * @fileoverview Shared client-state helpers for search pages.
 */

"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type StringSetUpdate = Set<string> | ((values: ReadonlySet<string>) => Set<string>);

/** Local storage key shared by hotel search surfaces for saved hotel state. */
export const HOTEL_WISHLIST_STORAGE_KEY = "hotelsSearch:wishlistHotels";

/**
 * Checks whether an unknown thrown value represents a cancelled client search.
 *
 * @param error - Unknown error value thrown by an abortable async operation.
 * @returns `true` when the value exposes the standard AbortError name.
 */
export function isAbortError(error: unknown): boolean {
  return (
    typeof error === "object" &&
    error !== null &&
    "name" in error &&
    error.name === "AbortError"
  );
}

/**
 * Creates lifecycle helpers for one in-flight search task.
 *
 * @returns Controller helpers that abort the previous task before a new task starts.
 */
export function useAbortableSearchTask() {
  const currentController = useRef<AbortController | null>(null);

  const clearSearchController = useCallback((controller: AbortController) => {
    if (currentController.current === controller) {
      currentController.current = null;
    }
  }, []);

  const abortCurrentSearch = useCallback(() => {
    currentController.current?.abort();
    currentController.current = null;
  }, []);

  const startSearchController = useCallback(() => {
    abortCurrentSearch();
    const controller = new AbortController();
    currentController.current = controller;
    return controller;
  }, [abortCurrentSearch]);

  useEffect(() => abortCurrentSearch, [abortCurrentSearch]);

  return { clearSearchController, startSearchController };
}

function readStoredStringSet(key: string): Set<string> {
  try {
    const stored = window.localStorage.getItem(key) ?? "[]";
    const parsed: unknown = JSON.parse(stored);
    return Array.isArray(parsed) && parsed.every((value) => typeof value === "string")
      ? new Set(parsed)
      : new Set();
  } catch {
    return new Set();
  }
}

function writeStoredStringSet(key: string, values: ReadonlySet<string>): void {
  try {
    window.localStorage.setItem(key, JSON.stringify([...values]));
  } catch {
    return;
  }
}

/**
 * Persists a string Set to localStorage while keeping the caller API Set-based.
 *
 * @param key - Local storage key that owns the persisted Set payload.
 * @returns Current values and a setter that accepts either a Set or functional update.
 */
export function usePersistentStringSet(
  key: string
): readonly [Set<string>, (update: StringSetUpdate) => Set<string>] {
  const [values, setValues] = useState<Set<string>>(new Set());
  const valuesRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    const storedValues = readStoredStringSet(key);
    valuesRef.current = storedValues;
    setValues(storedValues);
  }, [key]);

  const setStoredValues = useCallback(
    (update: StringSetUpdate) => {
      const nextValues =
        typeof update === "function" ? update(valuesRef.current) : update;
      valuesRef.current = nextValues;
      setValues(nextValues);
      writeStoredStringSet(key, nextValues);
      return nextValues;
    },
    [key]
  );

  return [values, setStoredValues] as const;
}

/**
 * Toggles one value in a Set without mutating the caller's Set.
 *
 * @param values - Source Set to copy before toggling.
 * @param value - String value to add or remove.
 * @returns The copied Set and whether the value was already present.
 */
export function toggleStringSetValue(
  values: ReadonlySet<string>,
  value: string
): { nextValues: Set<string>; wasPresent: boolean } {
  const nextValues = new Set(values);
  const wasPresent = nextValues.delete(value);
  if (!wasPresent) {
    nextValues.add(value);
  }
  return { nextValues, wasPresent };
}
