/**
 * @fileoverview Helpers for mapping recent search history items to form quick-select items.
 */

"use client";

import type { SearchHistoryItem } from "@schemas/stores";
import type { FieldValues } from "react-hook-form";
import type { QuickSelectItem } from "./search-form-shell";

type SafeParseResult<T> =
  | { success: true; data: T }
  | { success: false; error: unknown };

type SafeParseSchema<T> = {
  safeParse: (input: unknown) => SafeParseResult<T>;
};

export function buildRecentQuickSelectItems<Params extends FieldValues, Parsed>(
  recentSearches: SearchHistoryItem[],
  schema: SafeParseSchema<Parsed>,
  mapParsedToItem: (
    parsed: Parsed,
    search: SearchHistoryItem
  ) => QuickSelectItem<Params> | null
): QuickSelectItem<Params>[] {
  const items: QuickSelectItem<Params>[] = [];

  for (const search of recentSearches) {
    const parsed = schema.safeParse(search.params);
    if (!parsed.success) continue;

    const item = mapParsedToItem(parsed.data, search);
    if (item) items.push(item);
  }

  return items;
}
