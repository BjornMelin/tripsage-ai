/**
 * @fileoverview Shared client-state helpers for search pages.
 */

"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type StringSetUpdate = Set<string> | ((values: ReadonlySet<string>) => Set<string>);

/** Returns true for DOM abort errors produced by cancelled client searches. */
export function isAbortError(error: unknown): boolean {
  return error instanceof Error && error.name === "AbortError";
}

/** Creates a small lifecycle helper for one in-flight search task. */
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

/** Persists a string Set to localStorage while keeping the caller API Set-based. */
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

/** Toggles one value in a Set without mutating the caller's Set. */
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
