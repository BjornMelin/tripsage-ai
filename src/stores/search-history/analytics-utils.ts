/**
 * @fileoverview Shared search history analytics helpers.
 */

import type { SearchType } from "@schemas/search";
import type { SearchHistoryItem, ValidatedSavedSearch } from "@schemas/stores";
import type { SearchAnalytics } from "./types";

const MS_PER_DAY = 86_400_000;

export const createSearchTypeRecord = <T>(
  createValue: () => T
): Record<SearchType, T> => ({
  accommodation: createValue(),
  activity: createValue(),
  destination: createValue(),
  flight: createValue(),
});

const getDestinationLabel = (search: SearchHistoryItem): string | null => {
  const city = search.location?.city?.trim();
  const country = search.location?.country?.trim();

  if (city && country) return `${city}, ${country}`;
  if (city) return city;
  if (country) return country;

  const query = search.params.query;
  if (typeof query === "string" && query.trim().length > 0) return query.trim();

  return null;
};

/**
 * Build a fixed-length (N days) search trend series from per-day counts.
 *
 * Dates are normalized to UTC and returned as `YYYY-MM-DD` strings.
 *
 * @param searchesByDay - Map keyed by `YYYY-MM-DD` with daily counts.
 * @param now - Reference time (defaults to `new Date()`).
 * @param days - Number of days to include (defaults to `30`).
 * @returns Array of `{ date, count }` entries ordered oldest → newest.
 */
export const buildSearchTrends = (
  searchesByDay: Map<string, number>,
  now: Date = new Date(),
  days: number = 30
): Array<{ date: string; count: number }> => {
  const baseUtcMs = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  const trends: Array<{ date: string; count: number }> = [];

  for (let i = days - 1; i >= 0; i -= 1) {
    const date = new Date(baseUtcMs - i * MS_PER_DAY);
    const dateStr = date.toISOString().slice(0, 10);
    trends.push({ count: searchesByDay.get(dateStr) ?? 0, date: dateStr });
  }

  return trends;
};

export const computeSearchAnalytics = (
  recentSearches: SearchHistoryItem[],
  savedSearches: ValidatedSavedSearch[],
  now: Date = new Date(),
  days: number = 30
): SearchAnalytics => {
  const totalSearches = recentSearches.length;
  const searchesByType = createSearchTypeRecord(() => 0);

  const searchesByDay = new Map<string, number>();
  const searchesByHour = new Array<number>(24).fill(0);
  const destinationsByLabel = new Map<string, number>();

  let totalDuration = 0;

  for (const search of recentSearches) {
    searchesByType[search.searchType] += 1;
    totalDuration += search.searchDuration ?? 0;

    const ts = new Date(search.timestamp);
    const tsMs = ts.getTime();
    if (!Number.isFinite(tsMs)) continue;

    const dateKey = ts.toISOString().slice(0, 10);
    searchesByDay.set(dateKey, (searchesByDay.get(dateKey) ?? 0) + 1);

    const hour = ts.getUTCHours();
    if (!Number.isFinite(hour)) continue;
    searchesByHour[hour] += 1;

    if (search.searchType === "destination") {
      const label = getDestinationLabel(search);
      if (label)
        destinationsByLabel.set(label, (destinationsByLabel.get(label) ?? 0) + 1);
    }
  }

  const averageSearchDuration = totalSearches > 0 ? totalDuration / totalSearches : 0;

  const mostUsedSearchTypes = Object.entries(searchesByType)
    .map(([type, count]) => ({
      count,
      percentage: totalSearches > 0 ? (count / totalSearches) * 100 : 0,
      type: type as SearchType,
    }))
    .sort((a, b) => b.count - a.count);

  const searchTrends = buildSearchTrends(searchesByDay, now, days);

  const popularSearchTimes: Array<{ hour: number; count: number }> = searchesByHour.map(
    (count, hour) => ({ count, hour })
  );

  const topDestinations = [...destinationsByLabel.entries()]
    .map(([destination, count]) => ({ count, destination }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);

  return {
    averageSearchDuration,
    mostUsedSearchTypes,
    popularSearchTimes,
    savedSearchUsage: savedSearches
      .filter((search) => search.usageCount > 0)
      .sort((a, b) => b.usageCount - a.usageCount)
      .slice(0, 10)
      .map((search) => ({
        name: search.name,
        searchId: search.id,
        usageCount: search.usageCount,
      })),
    searchesByType,
    searchTrends,
    topDestinations,
    totalSearches,
  };
};
